from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import DailyScore, EpicMilestone, Habit, Income, LifeArea, User
from app.schemas import DailyScoreOut, HabitStatus, StatsOut
from app.services import rpg_logic

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("", response_model=StatsOut)
def get_stats(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    today = date.today()

    life_areas = list(db.scalars(select(LifeArea).where(LifeArea.user_id == current_user.id).order_by(LifeArea.name)))
    habits = list(db.scalars(select(Habit).where(Habit.user_id == current_user.id)))
    income = db.scalar(select(Income).where(Income.user_id == current_user.id))
    milestones = list(db.scalars(select(EpicMilestone).where(EpicMilestone.user_id == current_user.id)))
    todays_score = db.scalar(
        select(DailyScore).where(DailyScore.user_id == current_user.id, DailyScore.date == today)
    )

    return StatsOut(
        life_areas=life_areas,
        habits=[HabitStatus(type=h.type.value, streak=h.streak, done_today=h.last_done == today) for h in habits],
        income=income,
        milestones=milestones,
        todays_score=todays_score,
    )


@router.get("/daily-summary")
def preview_daily_summary(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    score, grade = rpg_logic.calculate_daily_score(db, current_user)
    return {"score": score, "grade": grade}


@router.post("/daily-summary/finalize", response_model=DailyScoreOut)
def finalize_daily_summary(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return rpg_logic.finalize_daily_summary(db, current_user)
