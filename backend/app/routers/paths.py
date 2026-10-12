from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import User
from app.services import daily_logs, paths, profiles, sub_classes

router = APIRouter(prefix="/paths", tags=["paths"])


def _logs(db: Session, user: User) -> dict:
    """Merged day logs from the earliest path start (and two weeks before it, for baselines) to today"""
    today = profiles.today(db, user)
    starts = [p.started_on for p in paths.user_paths(db, user)]
    since = min(starts + [today]) - timedelta(days=14)
    return {log.date.isoformat(): daily_logs.merged(log) for log in daily_logs.list_logs(db, user, since, today)}


def _view(db: Session, user: User, notes: list[str] | None = None) -> dict:
    logs = _logs(db, user)
    day = profiles.today(db, user).isoformat()
    scores = {sub_classes.code_of(s): sub_classes.score(s, logs, day)
              for s in sub_classes.custom_subs(db, user, active_only=True) if s.path_key}
    result = paths.view(db, user, logs, scores, notes)
    from app.services import books  # each path's books, unlocked or not
    by_path = books.for_paths(db, user)
    for path in result["active"]:
        path["books"] = by_path.get(path["key"], [])
    return result


@router.get("")
def list_paths(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """The paths you're on (level, title, the work-hard and be-smart halves, the story) and the ones you
    could start. Adjusts targets that are due their weekly check first."""
    notes = paths.adjust_targets(db, current_user, _logs(db, current_user))
    return _view(db, current_user, notes)


@router.post("/{key}")
def start_path(key: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Start (or restart) a path: its sub-classes join your classes, starting from your own baseline"""
    try:
        paths.start(db, current_user, key, _logs(db, current_user))
    except LookupError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))
    return _view(db, current_user)


@router.delete("/{key}")
def leave_path(key: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Leave a path: its sub-classes switch off; the XP you earned on it stays"""
    try:
        paths.leave(db, current_user, key)
    except LookupError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
    return _view(db, current_user)
