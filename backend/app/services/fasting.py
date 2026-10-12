"""Fasting: intermittent (a daily eating window, e.g. 16:8) and extended (24 h or more, water only).

A fast has a start, a goal in hours and, once over, an end. It's "completed" when it lasted at least
its goal. It belongs to the day it ended on (the user's local day), which is where its XP and its
part in Discipline and Health land.
"""

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Fast, User
from app.services import profiles

PRESETS = {
    "intermittent": [
        {"name": "14:10", "hours": 14, "note": "A gentle start"},
        {"name": "16:8", "hours": 16, "note": "The classic: skip breakfast or a late dinner"},
        {"name": "18:6", "hours": 18, "note": "A 6-hour eating window"},
        {"name": "20:4", "hours": 20, "note": "The warrior diet"},
        {"name": "OMAD", "hours": 23, "note": "One meal a day"},
    ],
    "extended": [
        {"name": "24 h", "hours": 24, "note": "Dinner to dinner"},
        {"name": "36 h", "hours": 36, "note": "Skip a whole day of food"},
        {"name": "48 h", "hours": 48, "note": "Two days: check with a doctor if you have a condition"},
        {"name": "72 h", "hours": 72, "note": "Three days: only with experience, and ideally a doctor's OK"},
    ],
}

# What the body is typically doing by this many hours (general guidance, it varies person to person)
STAGES = [
    (0, "Digesting", "Your last meal is still being absorbed."),
    (4, "Blood sugar settling", "Insulin falls back toward its baseline."),
    (12, "Fat burning rising", "Liver glycogen runs low and the body leans on fat."),
    (16, "Ketosis starting", "Ketone levels typically begin to climb."),
    (24, "Deep fast", "Glycogen is largely used up; drink water and get electrolytes."),
    (48, "Extended fast", "Hunger often eases; keep up salt, potassium and magnesium."),
    (72, "Long fast", "Break it gently, with a small meal. Longer fasts belong under medical supervision."),
]

EXTENDED_FROM = 24  # hours: a goal this long or longer is an extended fast
MAX_HOURS = 168


def hours(fast: Fast, now: datetime | None = None) -> float:
    end = fast.ended_at or now or datetime.now(timezone.utc)
    return max(0.0, (_aware(end) - _aware(fast.started_at)).total_seconds() / 3600)


def _aware(at: datetime) -> datetime:
    return at if at.tzinfo else at.replace(tzinfo=timezone.utc)


def stage(h: float) -> dict:
    start, name, detail = [s for s in STAGES if h >= s[0]][-1]
    following = next((s for s in STAGES if s[0] > h), None)
    return {"from_hours": start, "name": name, "detail": detail,
            "next": {"at_hours": following[0], "name": following[1]} if following else None}


def view(fast: Fast, zone: ZoneInfo) -> dict:
    """A fast as the apps show it: times, hours so far, the goal's end, the stage, and for an
    intermittent fast the eating window that follows"""
    h = hours(fast)
    goal_end = _aware(fast.started_at) + timedelta(hours=fast.goal_hours)
    window = None
    if fast.kind == "intermittent":
        opens = _aware(fast.ended_at) if fast.ended_at else goal_end
        window = {"opens": opens.isoformat(), "closes": (opens + timedelta(hours=max(0, 24 - fast.goal_hours))).isoformat()}
    return {
        "id": fast.id, "kind": fast.kind, "goal_hours": fast.goal_hours, "note": fast.note,
        "started_at": _aware(fast.started_at).isoformat(),
        "ended_at": _aware(fast.ended_at).isoformat() if fast.ended_at else None,
        "goal_end": goal_end.isoformat(),
        "hours": round(h, 2),
        "progress": round(min(1.0, h / fast.goal_hours), 3) if fast.goal_hours else None,
        "completed": h >= fast.goal_hours if fast.ended_at else None,  # null while it's running
        "active": fast.ended_at is None,
        "day": _aware(fast.ended_at).astimezone(zone).date().isoformat() if fast.ended_at else None,
        "stage": stage(h),
        "eating_window": window,
    }


def zone_of(db: Session, user: User) -> ZoneInfo:
    return ZoneInfo(profiles.get_profile(db, user).timezone)


def active(db: Session, user: User) -> Fast | None:
    return db.scalar(select(Fast).where(Fast.user_id == user.id, Fast.ended_at.is_(None)))


def history(db: Session, user: User, since: datetime | None = None) -> list[Fast]:
    query = select(Fast).where(Fast.user_id == user.id, Fast.ended_at.is_not(None))
    if since is not None:
        query = query.where(Fast.ended_at >= since)
    return list(db.scalars(query.order_by(Fast.ended_at.desc())))


def summaries(db: Session, user: User, since: date) -> list[dict]:
    """Ended fasts from `since` on, for the stats and XP: {day, kind, hours, goal, completed}"""
    zone = zone_of(db, user)
    start = datetime.combine(since, datetime.min.time(), zone)
    out = []
    for fast in history(db, user, start):
        h = hours(fast)
        out.append({"day": _aware(fast.ended_at).astimezone(zone).date().isoformat(), "kind": fast.kind,
                    "hours": round(h, 2), "goal": fast.goal_hours, "completed": h >= fast.goal_hours})
    return out


def fast_xp(h: float, completed: bool) -> int:
    """A completed fast: 1 XP an hour, at most 60"""
    return min(60, round(h)) if completed else 0
