from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import User
from app.services import character_stats, daily_logs, levels, profiles, unlocks

router = APIRouter(prefix="/customize", tags=["customize"])


class PartOffIn(BaseModel):
    stat: str = Field(max_length=10)
    part: str = Field(max_length=100)
    off: bool


def _parts(db: Session, user: User) -> list[dict]:
    """Every stat's parts with their standard weights"""
    profile = profiles.get_profile(db, user)
    day = profiles.today(db, user)
    sheet = character_stats.character_sheet(daily_logs.stats_input(db, user, day), day.isoformat(),
                                            profile.pushup_target, profile.sleep_target)
    return [
        {"code": code, "name": name, "parts": [{"name": c["name"], "weight": c["weight"]} for c in sheet["stats"][code]["components"]]}
        for code, name in character_stats.STATS
    ]


def _view(db: Session, user: User) -> dict:
    level = levels.summary(db, user)["level"]
    ladder = unlocks.ladder(level)
    return {
        "level": level,
        "ladder": ladder,
        "next": next((u for u in ladder if not u["unlocked"]), None),
        "off": (profiles.get_profile(db, user).customization or {}).get("off", {}),
        "stats": _parts(db, user),
    }


@router.get("")
def get_customization(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Your level, what each level unlocks, your settings, and every stat's parts"""
    return _view(db, current_user)


@router.put("/off")
def set_part_off(payload: PartOffIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Turn a part of a stat off or back on (unlocks at LV 7). At least one part of each stat stays on."""
    try:
        unlocks.require(levels.summary(db, current_user)["level"], "parts_off")
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    stat = next((s for s in _parts(db, current_user) if s["code"] == payload.stat), None)
    if not stat or payload.part not in [p["name"] for p in stat["parts"]]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No part '{payload.part}' in {payload.stat}")

    profile = profiles.get_profile(db, current_user)
    custom = dict(profile.customization or {})
    off = {code: list(names) for code, names in custom.get("off", {}).items()}
    names = set(off.get(payload.stat, []))
    names = names | {payload.part} if payload.off else names - {payload.part}
    if len(names) >= len(stat["parts"]):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Keep at least one part of {stat['name']} on")
    off[payload.stat] = sorted(names)
    custom["off"] = {code: n for code, n in off.items() if n}
    profile.customization = custom  # a new dict, so the JSON column is saved
    db.commit()
    return _view(db, current_user)


@router.delete("")
def reset(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Back to the standard stats (always allowed)"""
    profiles.get_profile(db, current_user).customization = {}
    db.commit()
    return _view(db, current_user)
