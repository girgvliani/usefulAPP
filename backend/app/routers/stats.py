from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import DailyScore, EpicMilestone, Habit, Income, LifeArea, User
from app.schemas import CategoryResult, CharacterDay, CharacterSheetOut, DailyScoreOut, HabitStatus, LevelOut, StatResult, StatsOut, StreaksOut
from app.services import sub_classes, achievements, character_stats, daily_logs, levels, profiles, rpg_logic, streaks, tips

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


def _sheet(db: Session, user: User, data: dict, day: date, own: tuple | None = None) -> dict:
    """Shared formulas, personal targets, and the user's own customization and sub-classes (their view
    only). own: (custom sub-classes, hidden built-ins), loaded once when building many days."""
    profile = profiles.get_profile(db, user)
    subs, hidden = own or (sub_classes.custom_subs(db, user, active_only=True), sub_classes.hidden_builtins(db, user))
    sheet = character_stats.character_sheet(data, day.isoformat(), profile.pushup_target, profile.sleep_target,
                                            profile.customization)
    return sub_classes.personal_sheet(sheet, subs, hidden, data.get('daily_logs', {}), day.isoformat())


@router.get("/character", response_model=CharacterSheetOut)
def character_sheet(day: date | None = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Every stat and the six categories they make up, for one day (default: today in the configured timezone)."""
    day = day or profiles.today(db, current_user)
    data = daily_logs.stats_input(db, current_user, day)
    sheet = _sheet(db, current_user, data, day)
    grade = lambda score: character_stats.grade(score) if score is not None else None
    return CharacterSheetOut(
        date=day,
        overall=sheet['overall'],
        overall_grade=grade(sheet['overall']),
        categories=[
            CategoryResult(key=key, name=name, score=sheet['categories'][key], grade=grade(sheet['categories'][key]),
                           stats=sheet['layout'][key])
            for key, name, _ in character_stats.CATEGORIES
        ],
        stats=[
            StatResult(code=code, name=sheet['names'][code], grade=grade(result['score']), **result)
            for code, result in sheet['stats'].items()
        ],
    )


MAX_HISTORY_DAYS = 92


@router.get("/character/history", response_model=list[CharacterDay])
def character_history(
    start: date, end: date | None = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Every stat's and category's score for each day from start to end (default today), for charts."""
    end = end or profiles.today(db, current_user)
    if end < start or (end - start).days >= MAX_HISTORY_DAYS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Range must be 1-{MAX_HISTORY_DAYS} days")
    data = daily_logs.stats_input(db, current_user, end, start)
    own = (sub_classes.custom_subs(db, current_user, active_only=True), sub_classes.hidden_builtins(db, current_user))
    history = []
    for offset in range((end - start).days + 1):
        day = start + timedelta(days=offset)
        sheet = _sheet(db, current_user, data, day, own)
        history.append(CharacterDay(
            date=day, overall=sheet['overall'], scores={code: stat['score'] for code, stat in sheet['stats'].items()},
            categories=sheet['categories'],
        ))
    return history


@router.get("/tip")
def daily_tip(when: str = "morning", current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """The daily tip: morning = the biggest gain available today, evening = what's still open before midnight."""
    if when == "evening":
        return {"when": "evening", **tips.evening(db, current_user)}
    day = profiles.today(db, current_user)
    sheet = _sheet(db, current_user, daily_logs.stats_input(db, current_user, day), day)
    return {"when": "morning", **tips.morning(db, current_user, sheet)}


@router.get("/streaks", response_model=StreaksOut)
def get_streaks(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Every streak with today's state, plus a mood for the home-screen widget."""
    return streaks.streaks(db, current_user)


@router.get("/level", response_model=LevelOut)
def get_level(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Global level and XP from every source, plus what today has earned so far. Checks achievements
    first, so anything just reached is in the XP and in new_achievements."""
    achievements.evaluate(db, current_user)
    return {**levels.summary(db, current_user), "new_achievements": achievements.unseen(db, current_user)}
