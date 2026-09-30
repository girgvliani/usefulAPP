from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Habit, PushupLog, User
from app.schemas import HabitStatus, PushupIn, PushupLogOut, ShowerResult, WorkoutResult
from app.serializers import xp_result_to_schema
from app.services import rpg_logic

router = APIRouter(prefix="/habits", tags=["habits"])


@router.get("", response_model=list[HabitStatus])
def list_habits(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    today = date.today()
    habits = db.scalars(select(Habit).where(Habit.user_id == current_user.id))
    return [HabitStatus(type=h.type.value, streak=h.streak, done_today=h.last_done == today) for h in habits]


@router.get("/workout/history", response_model=list[PushupLogOut])
def pushup_history(
    days: int = Query(default=30, ge=1, le=400),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    since = date.today() - timedelta(days=days - 1)
    return list(db.scalars(
        select(PushupLog).where(PushupLog.user_id == current_user.id, PushupLog.date >= since).order_by(PushupLog.date.desc())
    ))


@router.delete("/workout/history/{log_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pushup_log(log_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """For a wrong entry. XP and streak aren't recalculated; the stats (PS, DIS) read the history and do update."""
    log = db.scalar(select(PushupLog).where(PushupLog.user_id == current_user.id, PushupLog.id == log_id))
    if not log:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Push-up entry not found")
    db.delete(log)
    db.commit()


@router.post("/workout", response_model=WorkoutResult)
def log_workout(payload: PushupIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = rpg_logic.track_pushups(db, current_user, payload.count)
    return WorkoutResult(
        met_requirement=result["met_requirement"],
        streak=result["streak"],
        bonus_xp=result["bonus_xp"],
        consistency_bonus=result["consistency_bonus"],
        xp_result=xp_result_to_schema(result["xp_result"]),
    )


@router.post("/shower", response_model=ShowerResult)
def log_shower(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = rpg_logic.check_shower(db, current_user)
    return ShowerResult(
        already_logged=result["already_logged"],
        streak=result["streak"],
        xp_result=xp_result_to_schema(result.get("xp_result")),
    )
