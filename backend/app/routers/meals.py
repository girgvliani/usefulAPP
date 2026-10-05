from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Meal, User
from app.rate_limit import limiter
from app.schemas import DayMeals, MealIn, MealOut, MealUpdate, NutritionTargets
from app.services import daily_logs, nutrition, profiles

router = APIRouter(prefix="/meals", tags=["meals"])

MAX_PHOTO_BYTES = 10 * 1024 * 1024
PHOTO_TYPES = {"image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"}


def _owned_meal(db: Session, user: User, meal_id: int) -> Meal:
    meal = db.scalar(select(Meal).where(Meal.user_id == user.id, Meal.id == meal_id))
    if not meal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meal not found")
    return meal


def _when(db: Session, user: User, eaten_at: datetime | None) -> datetime:
    """In the user's timezone; naive times are read as the user's local time. No future meals."""
    zone = ZoneInfo(profiles.get_profile(db, user).timezone)
    now = datetime.now(zone)
    moment = now if eaten_at is None else (eaten_at.replace(tzinfo=zone) if eaten_at.tzinfo is None else eaten_at.astimezone(zone))
    if moment > now + timedelta(minutes=5):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="That meal is in the future")
    return moment


def _save(db: Session, user: User, name: str, items: list[dict], moment: datetime, meal_type: str | None,
          source: str, confidence: float | None = None) -> Meal:
    meal = Meal(
        user_id=user.id, date=moment.date(), eaten_at=moment, meal_type=meal_type or nutrition.meal_type_for(moment),
        name=name, items=items, source=source, confidence=confidence, **nutrition.totals(items),
    )
    db.add(meal)
    db.commit()
    db.refresh(meal)
    return meal


@router.get("", response_model=DayMeals)
def day_meals(day: date | None = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """A day's meals (default today) with totals and your targets."""
    day = day or profiles.today(db, current_user)
    meals = list(db.scalars(
        select(Meal).where(Meal.user_id == current_user.id, Meal.date == day).order_by(Meal.eaten_at)
    ))
    return DayMeals(
        date=day, meals=meals, **nutrition.totals([{k: getattr(m, k) for k in ("kcal", "protein", "carbs", "fat")} for m in meals]),
        targets=NutritionTargets(**daily_logs.nutrition_targets(db, current_user, day)),
    )


@router.post("/photo", response_model=MealOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/hour")
def log_photo(
    request: Request,
    photo: UploadFile = File(...),
    eaten_at: datetime | None = Form(default=None),
    note: str | None = Form(default=None, max_length=300),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Reads the meal from a photo with Gemini and saves it. eaten_at: when the photo was taken."""
    if photo.content_type not in PHOTO_TYPES:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Send a JPEG, PNG, WebP or HEIC photo")
    image = photo.file.read(MAX_PHOTO_BYTES + 1)
    if len(image) > MAX_PHOTO_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Photo is over 10 MB")
    moment = _when(db, current_user, eaten_at)
    try:
        read = nutrition.read_photo(image, photo.content_type, note)
    except nutrition.PhotoError as e:
        # Busy / out of quota is Google's side and passes; anything else is about this photo
        code = status.HTTP_503_SERVICE_UNAVAILABLE if e.busy else status.HTTP_422_UNPROCESSABLE_ENTITY
        raise HTTPException(status_code=code, detail=str(e))
    return _save(db, current_user, read["name"], read["items"], moment, None, "photo", read["confidence"])


@router.post("", response_model=MealOut, status_code=status.HTTP_201_CREATED)
def log_meal(payload: MealIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """A meal typed in by hand."""
    moment = _when(db, current_user, payload.eaten_at)
    items = [item.model_dump() for item in payload.items]
    return _save(db, current_user, payload.name, items, moment, payload.meal_type, "manual")


@router.get("/{meal_id}", response_model=MealOut)
def get_meal(meal_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _owned_meal(db, current_user, meal_id)


@router.patch("/{meal_id}", response_model=MealOut)
def update_meal(meal_id: int, payload: MealUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Fix what the photo reader got wrong: rename, change the type, or replace the items (totals follow)."""
    meal = _owned_meal(db, current_user, meal_id)
    if payload.name is not None:
        meal.name = payload.name
    if payload.meal_type is not None:
        meal.meal_type = payload.meal_type
    if payload.items is not None:
        meal.items = [item.model_dump() for item in payload.items]
        for key, value in nutrition.totals(meal.items).items():
            setattr(meal, key, value)
    db.commit()
    db.refresh(meal)
    return meal


@router.delete("/{meal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_meal(meal_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.delete(_owned_meal(db, current_user, meal_id))
    db.commit()
