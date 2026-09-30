"""Per-user settings, and "today" in the user's own timezone."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import User, UserProfile

# Starting targets for a new account; every user changes them in their profile
NEW_USER_DEFAULTS = {"currency": "USD", "pushup_target": 50, "steps_target": 8000, "sleep_target": 7.5}


def get_profile(db: Session, user: User) -> UserProfile:
    """Created on first use, so every account has one."""
    profile = db.scalar(select(UserProfile).where(UserProfile.user_id == user.id))
    if profile is None:
        profile = UserProfile(user_id=user.id, timezone=settings.timezone, **NEW_USER_DEFAULTS)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


def now(db: Session, user: User) -> datetime:
    return datetime.now(ZoneInfo(get_profile(db, user).timezone))


def today(db: Session, user: User) -> date:
    return now(db, user).date()
