from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Fast, User
from app.services import fasting

router = APIRouter(prefix="/fasts", tags=["fasting"])


class FastIn(BaseModel):
    kind: Literal["intermittent", "extended"]
    goal_hours: float = Field(ge=1, le=fasting.MAX_HOURS)
    started_at: datetime | None = None  # earlier than now when you started before opening the app
    note: str | None = Field(default=None, max_length=200)


class FastUpdate(BaseModel):
    goal_hours: float | None = Field(default=None, ge=1, le=fasting.MAX_HOURS)
    started_at: datetime | None = None
    ended_at: datetime | None = None
    note: str | None = Field(default=None, max_length=200)


class EndIn(BaseModel):
    ended_at: datetime | None = None  # defaults to now


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(at: datetime) -> datetime:
    return at if at.tzinfo else at.replace(tzinfo=timezone.utc)


def _get(db: Session, user: User, fast_id: int) -> Fast:
    fast = db.scalar(select(Fast).where(Fast.id == fast_id, Fast.user_id == user.id))
    if not fast:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such fast")
    return fast


def _check_times(started: datetime, ended: datetime | None) -> None:
    now = _now() + timedelta(minutes=5)  # a little clock drift is fine
    if _aware(started) > now:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A fast can't start in the future")
    if _aware(started) < _now() - timedelta(days=14):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="That start is more than two weeks ago")
    if ended is not None:
        if _aware(ended) > now:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A fast can't end in the future")
        if _aware(ended) <= _aware(started):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The end has to be after the start")
        if (_aware(ended) - _aware(started)) > timedelta(hours=fasting.MAX_HOURS):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Fasts are capped at 7 days")


@router.get("")
def overview(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """The fast running now (if any), the last 60 fasts, presets, stages and a few totals"""
    zone = fasting.zone_of(db, current_user)
    running = fasting.active(db, current_user)
    past = fasting.history(db, current_user)
    done = [f for f in past if fasting.hours(f) >= f.goal_hours]
    week_ago = _now() - timedelta(days=7)
    return {
        "active": fasting.view(running, zone) if running else None,
        "history": [fasting.view(f, zone) for f in past[:60]],
        "presets": fasting.PRESETS,
        "stages": [{"at_hours": h, "name": n, "detail": d} for h, n, d in fasting.STAGES],
        "totals": {
            "completed": len(done),
            "this_week": sum(1 for f in done if _aware(f.ended_at) >= week_ago),
            "longest_hours": round(max((fasting.hours(f) for f in past), default=0), 1),
        },
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def start(payload: FastIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Start a fast (now, or at an earlier time). Only one runs at a time."""
    if fasting.active(db, current_user):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A fast is already running: end it first")
    started = payload.started_at or _now()
    _check_times(started, None)
    fast = Fast(user_id=current_user.id, kind=payload.kind, goal_hours=payload.goal_hours, started_at=started, note=payload.note)
    db.add(fast)
    db.commit()
    db.refresh(fast)
    return fasting.view(fast, fasting.zone_of(db, current_user))


@router.post("/{fast_id}/end")
def end(fast_id: int, payload: EndIn | None = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Break the fast now (or at the time given). It counts as completed if it lasted its goal."""
    fast = _get(db, current_user, fast_id)
    if fast.ended_at:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="That fast is already over")
    ended = (payload.ended_at if payload else None) or _now()
    _check_times(fast.started_at, ended)
    fast.ended_at = ended
    db.commit()
    return fasting.view(fast, fasting.zone_of(db, current_user))


@router.patch("/{fast_id}")
def update(fast_id: int, payload: FastUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Fix a start or end time, the goal or the note"""
    fast = _get(db, current_user, fast_id)
    changes = payload.model_dump(exclude_unset=True)
    started = changes.get("started_at") or fast.started_at
    ended = changes["ended_at"] if "ended_at" in changes else fast.ended_at
    if ended is None and fast.ended_at is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="An ended fast keeps its end time")
    _check_times(started, ended)
    for key, value in changes.items():
        if value is not None or key == "note":
            setattr(fast, key, value)
    db.commit()
    return fasting.view(fast, fasting.zone_of(db, current_user))


@router.delete("/{fast_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove(fast_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Delete a fast (a mistake, or a running one you didn't mean to start)"""
    db.delete(_get(db, current_user, fast_id))
    db.commit()
