"""Calorie and protein targets, and reading meals from photos with Gemini.

Targets: Mifflin-St Jeor BMR (Mifflin et al. 1990) x an activity factor from the week's steps, then
-500 kcal/day while a weight goal points down (~0.5 kg/week) or +300 while it points up, never below a
safe floor. Protein: 1.6 g per kg (Morton et al. 2018: gains in strength and muscle plateau around it).
"""

import base64
import json
import logging
import time
from datetime import date, datetime

import httpx

from app.config import settings

logger = logging.getLogger("life_rpg")

LOSE_KCAL = -500
GAIN_KCAL = 300
MAX_DEFICIT = 0.25  # never cut more than a quarter of what you burn
FLOOR_KCAL = {"male": 1500, "female": 1200}
PROTEIN_G_PER_KG = 1.6
STEP_FACTORS = [(5000, 1.2), (7500, 1.375), (10000, 1.55)]  # 10k+ steps: 1.725


class PhotoError(Exception):
    """The photo couldn't be read: no key set, not food, or Gemini failed. busy: worth trying again soon."""

    def __init__(self, message: str, busy: bool = False):
        super().__init__(message)
        self.busy = busy


def activity_factor(avg_steps: float | None) -> float:
    if avg_steps is None:
        return 1.375  # no step data yet: assume lightly active
    for limit, factor in STEP_FACTORS:
        if avg_steps < limit:
            return factor
    return 1.725


def targets(profile, weight_kg: float | None, avg_steps: float | None, direction: str | None, today: date) -> dict:
    """direction: "decrease" / "increase" from the active weight goal, or None to maintain."""
    missing = [label for label, value in (
        ("height", profile.height_cm), ("birth year", profile.birth_year), ("sex", profile.sex), ("weight", weight_kg),
    ) if value is None]
    protein = round(PROTEIN_G_PER_KG * weight_kg) if weight_kg else None
    adjustment = LOSE_KCAL if direction == "decrease" else GAIN_KCAL if direction == "increase" else 0
    if missing:
        return {"calories": None, "protein": protein, "bmr": None, "tdee": None, "adjustment": adjustment, "missing": missing}

    age = today.year - profile.birth_year
    bmr = 10 * weight_kg + 6.25 * profile.height_cm - 5 * age + (5 if profile.sex == "male" else -161)
    tdee = bmr * activity_factor(avg_steps)
    calories = tdee + max(adjustment, -MAX_DEFICIT * tdee)
    calories = max(calories, FLOOR_KCAL[profile.sex])
    return {
        "calories": round(calories), "protein": protein, "bmr": round(bmr), "tdee": round(tdee),
        "adjustment": adjustment, "missing": [],
    }


def meal_type_for(moment: datetime) -> str:
    minutes = moment.hour * 60 + moment.minute
    if 5 * 60 <= minutes < 10 * 60 + 30:
        return "breakfast"
    if minutes < 15 * 60:
        return "lunch"
    if minutes < 17 * 60 + 30:
        return "snack"
    if minutes < 22 * 60:
        return "dinner"
    return "snack"


def totals(items: list[dict]) -> dict:
    return {key: round(sum(item.get(key) or 0 for item in items), 1) for key in ("kcal", "protein", "carbs", "fat")}


# ---- Gemini

PROMPT = """You estimate nutrition from meal photos for a calorie tracker.
List every food and drink you can see, with a realistic portion in grams and its calories, protein,
carbohydrates and fat for that portion. Use typical recipes; the user is in Georgia, so recognise Georgian
dishes (khachapuri, khinkali, lobiani, mtsvadi, pkhali, badrijani, churchkhela) when you see them.
Give the meal a short name. If the photo shows no food or drink, set is_food to false and leave items empty.
confidence is your own 0-1 estimate of how accurate the calories are."""

SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "is_food": {"type": "BOOLEAN"},
        "meal_name": {"type": "STRING"},
        "confidence": {"type": "NUMBER"},
        "items": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "name": {"type": "STRING"},
                    "grams": {"type": "NUMBER"},
                    "kcal": {"type": "NUMBER"},
                    "protein": {"type": "NUMBER"},
                    "carbs": {"type": "NUMBER"},
                    "fat": {"type": "NUMBER"},
                },
                "required": ["name", "grams", "kcal", "protein", "carbs", "fat"],
            },
        },
    },
    "required": ["is_food", "meal_name", "confidence", "items"],
}


def _ask_gemini(model: str, image: bytes, mime: str, note: str | None) -> httpx.Response:
    prompt = PROMPT + (f"\nThe user adds: {note}" if note else "")
    body = {
        "contents": [{"parts": [
            {"inline_data": {"mime_type": mime, "data": base64.b64encode(image).decode()}},
            {"text": prompt},
        ]}],
        "generationConfig": {"responseMimeType": "application/json", "responseSchema": SCHEMA, "temperature": 0.2},
    }
    return httpx.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        headers={"x-goog-api-key": settings.gemini_api_key},
        json=body,
        timeout=CALL_TIMEOUT,
    )


# Google says "high demand" (503) or times out now and then on the free tier; those pass in seconds
BUSY = {500, 502, 503, 504}
CALL_TIMEOUT = 30
RETRY_WAIT = 2  # seconds before asking the same model again
TIME_BUDGET = 75  # the phone app waits 90 s for the whole request


def _ask_models(image: bytes, mime: str, note: str | None) -> httpx.Response | None:
    """The first good answer. Each model gets a second try when it's busy; a used-up daily limit (429)
    or a second busy answer moves on to the next model. None when every try timed out."""
    started = time.monotonic()
    response = None
    for model in (settings.gemini_model, settings.gemini_fallback_model):
        for attempt in range(2):
            if time.monotonic() - started > TIME_BUDGET - CALL_TIMEOUT:
                return response
            try:
                response = _ask_gemini(model, image, mime, note)
            except httpx.TransportError as e:  # timeouts and dropped connections
                logger.warning("Gemini %s: %s", model, e)
                break  # a slow model stays slow for a while; try the next one
            else:
                if response.status_code not in BUSY:
                    if response.status_code == 429:
                        logger.warning("Gemini %s: daily limit (429)", model)
                        break  # the limit won't lift in seconds; try the next model
                    return response
                logger.warning("Gemini %s busy (%s): %s", model, response.status_code, response.text[:200])
            if attempt == 0:
                time.sleep(RETRY_WAIT)
    return response


def read_photo(image: bytes, mime: str, note: str | None = None) -> dict:
    """{name, confidence, items} for a meal photo. Retries a busy model once, then falls back to the
    second model (also when the first is rate-limited: the free tier has a daily cap)."""
    if not settings.gemini_api_key:
        raise PhotoError("Photo logging isn't set up on the server (no GEMINI_API_KEY)")

    response = _ask_models(image, mime, note)
    if response is None or response.status_code in BUSY:
        raise PhotoError("Google's photo reader is busy right now; try again in a minute", busy=True)
    if response.status_code != 200:
        logger.warning("Gemini %s: %s", response.status_code, response.text[:500])
        raise PhotoError("The free daily limit for photo reading is used up; try later" if response.status_code == 429
                         else f"The photo reader failed ({response.status_code})", busy=response.status_code == 429)
    try:
        text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        result = json.loads(text)
    except (KeyError, IndexError, ValueError) as e:
        raise PhotoError("The photo reader gave an answer we couldn't use") from e

    if not result.get("is_food") or not result.get("items"):
        raise PhotoError("That doesn't look like food")
    items = [
        {
            "name": str(item["name"])[:120],
            "grams": max(0.0, float(item.get("grams") or 0)),
            **{key: max(0.0, float(item.get(key) or 0)) for key in ("kcal", "protein", "carbs", "fat")},
        }
        for item in result["items"][:30]
    ]
    confidence = result.get("confidence")
    return {
        "name": str(result.get("meal_name") or "Meal")[:200],
        "confidence": min(1.0, max(0.0, float(confidence))) if confidence is not None else None,
        "items": items,
    }
