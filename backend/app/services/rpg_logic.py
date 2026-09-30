"""
Business logic ported from the original life_rpg.py PersonalLifeRPG class.
Formulas and constants are kept identical to the original CLI so XP/level
math behaves exactly the same as before - operating on Postgres rows
(scoped per-user) instead of an in-memory dict loaded from JSON.
"""

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.services import profiles

from app.models import (
    Achievement,
    DailyScore,
    EpicMilestone,
    Habit,
    HabitType,
    Income,
    LifeArea,
    Project,
    PushupLog,
    ScreenTimeLog,
    SocialInteraction,
    Todo,
    User,
)

DAILY_DECAY = 5
SCREEN_TIME_LIMIT = 2
SOCIAL_LIMIT = 3

# General areas for a new account; everyone renames or adds their own
DEFAULT_LIFE_AREAS = [
    "Health - Exercise",
    "Health - Sleep",
    "Health - Hygiene",
    "Learning - Study",
    "Learning - Reading",
    "Career - Work Skills",
    "Career - Side Projects",
    "Mind - Focus",
    "Social Balance",
]

# Habit and social XP land in these areas by name, so they can't be renamed or deleted
PROTECTED_AREAS = {"Health - Exercise", "Health - Sleep", "Health - Hygiene", "Social Balance"}


ACHIEVEMENT_THRESHOLDS = {5: "Bronze", 10: "Silver", 20: "Gold", 30: "Platinum"}


def seed_new_user(db: Session, user: User) -> None:
    """Neutral starting rows for a new account: general life areas, habits, no milestones, no income goal.
    Everyone adds their own milestones and goals."""
    for name in DEFAULT_LIFE_AREAS:
        db.add(LifeArea(user_id=user.id, name=name, level=1, xp=0))
    db.add(Habit(user_id=user.id, type=HabitType.shower, streak=0))
    db.add(Habit(user_id=user.id, type=HabitType.workout, streak=0))
    db.add(Income(user_id=user.id, monthly_goal=0, current_month_earnings=0, target_month=""))
    db.add(SocialInteraction(user_id=user.id, week_start=date.today(), weekly_count=0))
    db.commit()
    profiles.get_profile(db, user)


def calculate_level(xp: int) -> int:
    return (xp // 150) + 1


def calculate_time_multiplier(deadline: date, completed: date) -> float:
    days_diff = (completed - deadline).days
    if days_diff <= 0:
        return 1.5
    elif days_diff <= 7:
        return 1.0
    return 0.5


def _life_areas(db: Session, user: User) -> list[LifeArea]:
    return list(db.scalars(select(LifeArea).where(LifeArea.user_id == user.id)))


def get_life_area(db: Session, user: User, area_id: int) -> LifeArea | None:
    return db.scalar(select(LifeArea).where(LifeArea.user_id == user.id, LifeArea.id == area_id))


def check_achievements(db: Session, user: User, area: LifeArea, level: int) -> str | None:
    tier = ACHIEVEMENT_THRESHOLDS.get(level)
    if not tier:
        return None
    name = f"{area.name} - {tier} Tier"
    exists = db.scalar(select(Achievement).where(Achievement.user_id == user.id, Achievement.name == name))
    if exists:
        return None
    db.add(Achievement(user_id=user.id, name=name))
    return name


def add_xp(db: Session, user: User, area: LifeArea, points: int) -> dict:
    """Add XP to a life area, recalculating level and checking achievements (matches original add_xp)."""
    old_level = area.level
    area.xp += points
    area.last_active = date.today()
    area.level = calculate_level(area.xp)

    achievement = None
    if area.level > old_level:
        achievement = check_achievements(db, user, area, area.level)

    db.commit()
    db.refresh(area)
    return {"area": area, "leveled_up": area.level > old_level, "achievement": achievement}


def apply_daily_decay(db: Session, user: User) -> None:
    """Runs once per calendar day per user, mirroring the original 'decay on load' behavior."""
    today = date.today()
    if user.last_login == today:
        return

    days_passed = (today - user.last_login).days
    if days_passed > 0:
        for area in _life_areas(db, user):
            decay_amount = DAILY_DECAY * days_passed
            area.xp = max(0, area.xp - decay_amount)
            area.level = calculate_level(area.xp)
    user.last_login = today
    db.commit()


def _update_habit_streak(habit: Habit, today: date) -> None:
    if habit.last_done:
        diff = (today - habit.last_done).days
        if diff == 1:
            habit.streak += 1
        elif diff > 1:
            habit.streak = 1
    else:
        habit.streak = 1


def track_pushups(db: Session, user: User, count: int) -> dict:
    today = date.today()
    habit = db.scalar(select(Habit).where(Habit.user_id == user.id, Habit.type == HabitType.workout))

    _update_habit_streak(habit, today)
    habit.last_done = today
    db.add(PushupLog(user_id=user.id, date=today, count=count))

    requirement = profiles.get_profile(db, user).pushup_target
    result = {"met_requirement": count >= requirement, "bonus_xp": 0, "consistency_bonus": 0, "xp_result": None}
    if count >= requirement:
        xp = DAILY_DECAY
        if count > requirement:
            bonus = min((count - requirement) // 10, 10)
            xp += bonus
            result["bonus_xp"] = bonus
        if habit.streak >= 7:
            consistency_bonus = habit.streak // 7 * 5
            xp += consistency_bonus
            result["consistency_bonus"] = consistency_bonus

        area = db.scalar(select(LifeArea).where(LifeArea.user_id == user.id, LifeArea.name == "Health - Exercise"))
        result["xp_result"] = add_xp(db, user, area, xp)

    db.commit()
    result["streak"] = habit.streak
    return result


def check_shower(db: Session, user: User) -> dict:
    today = date.today()
    habit = db.scalar(select(Habit).where(Habit.user_id == user.id, Habit.type == HabitType.shower))

    if habit.last_done == today:
        return {"already_logged": True, "streak": habit.streak}

    _update_habit_streak(habit, today)
    habit.last_done = today

    area = db.scalar(select(LifeArea).where(LifeArea.user_id == user.id, LifeArea.name == "Health - Hygiene"))
    xp_result = add_xp(db, user, area, 10)

    db.commit()
    return {"already_logged": False, "streak": habit.streak, "xp_result": xp_result}


def log_sleep(db: Session, user: User, hours: float) -> dict:
    if 7 <= hours <= 8:
        xp = 20
    elif hours >= 6:
        xp = 10
    else:
        xp = 5
    area = db.scalar(select(LifeArea).where(LifeArea.user_id == user.id, LifeArea.name == "Health - Sleep"))
    return add_xp(db, user, area, xp)


def _apply_flat_penalty(db: Session, user: User, penalty: int) -> None:
    """Distributes a penalty evenly across all areas without recalculating level -
    matches the original track_screen_time/log_social_interaction behavior exactly."""
    areas = _life_areas(db, user)
    if not areas:
        return
    per_area = penalty // len(areas)
    for area in areas:
        area.xp = max(0, area.xp - per_area)
    db.commit()


def track_screen_time(db: Session, user: User, hours: float) -> dict:
    today = date.today()
    existing = db.scalar(select(ScreenTimeLog).where(ScreenTimeLog.user_id == user.id, ScreenTimeLog.date == today))
    if existing:
        existing.hours = hours
    else:
        db.add(ScreenTimeLog(user_id=user.id, date=today, hours=hours))
    db.commit()

    if hours > SCREEN_TIME_LIMIT:
        penalty = int((hours - SCREEN_TIME_LIMIT) * 10)
        _apply_flat_penalty(db, user, penalty)
        return {"over_limit": True, "penalty": penalty}
    return {"over_limit": False, "penalty": 0}


def log_social_interaction(db: Session, user: User) -> dict:
    today = date.today()
    social = db.scalar(select(SocialInteraction).where(SocialInteraction.user_id == user.id))

    if (today - social.week_start).days >= 7:
        social.weekly_count = 0
        social.week_start = today

    social.weekly_count += 1
    db.commit()

    if social.weekly_count > SOCIAL_LIMIT:
        penalty = (social.weekly_count - SOCIAL_LIMIT) * 20
        _apply_flat_penalty(db, user, penalty)
        return {"over_limit": True, "count": social.weekly_count, "penalty": penalty}

    area = db.scalar(select(LifeArea).where(LifeArea.user_id == user.id, LifeArea.name == "Social Balance"))
    xp_result = add_xp(db, user, area, 5)
    return {"over_limit": False, "count": social.weekly_count, "xp_result": xp_result}


def add_project(db: Session, user: User, name: str, value: int, deadline: date) -> Project:
    project = Project(user_id=user.id, name=name, value=value, deadline=deadline, completed=False)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def complete_project(db: Session, user: User, project_id: int) -> Project | None:
    project = db.scalar(
        select(Project).where(Project.user_id == user.id, Project.id == project_id, Project.completed == False)  # noqa: E712
    )
    if not project:
        return None

    today = date.today()
    project.completed = True
    project.completion_date = today

    income = db.scalar(select(Income).where(Income.user_id == user.id))
    income.current_month_earnings += project.value

    multiplier = calculate_time_multiplier(project.deadline, today)
    base_xp = project.value // 10
    xp = int(base_xp * multiplier)

    work_areas = [a for a in _life_areas(db, user) if a.name.startswith("Work Skills")]
    if work_areas:
        xp_per_area = xp // len(work_areas)
        for area in work_areas:
            add_xp(db, user, area, xp_per_area)

    db.commit()
    db.refresh(project)
    return project


def add_todo(db: Session, user: User, task: str, area_id: int, base_xp: int, deadline: date) -> Todo | None:
    area = get_life_area(db, user, area_id)
    if not area:
        return None
    todo = Todo(user_id=user.id, task=task, area_id=area_id, base_xp=base_xp, deadline=deadline, completed=False)
    db.add(todo)
    db.commit()
    db.refresh(todo)
    return todo


def complete_todo(db: Session, user: User, todo_id: int) -> Todo | None:
    todo = db.scalar(
        select(Todo).where(Todo.user_id == user.id, Todo.id == todo_id, Todo.completed == False)  # noqa: E712
    )
    if not todo:
        return None

    today = date.today()
    todo.completed = True
    todo.completion_date = today

    multiplier = calculate_time_multiplier(todo.deadline, today)
    xp = int(todo.base_xp * multiplier)

    area = get_life_area(db, user, todo.area_id)
    add_xp(db, user, area, xp)

    db.commit()
    db.refresh(todo)
    return todo


def complete_epic_milestone(db: Session, user: User, key: str) -> EpicMilestone | None:
    milestone = db.scalar(select(EpicMilestone).where(EpicMilestone.user_id == user.id, EpicMilestone.key == key))
    if not milestone or milestone.completed:
        return None

    milestone.completed = True
    areas = _life_areas(db, user)
    if areas:
        xp_per_area = milestone.xp_reward // len(areas)
        for area in areas:
            add_xp(db, user, area, xp_per_area)

    db.commit()
    db.refresh(milestone)
    return milestone


def manual_xp_adjustment(db: Session, user: User, area_id: int, xp: int) -> LifeArea | None:
    area = get_life_area(db, user, area_id)
    if not area:
        return None
    add_xp(db, user, area, xp)
    return area


def calculate_daily_score(db: Session, user: User) -> tuple[int, str]:
    today = date.today()
    score = 0

    shower = db.scalar(select(Habit).where(Habit.user_id == user.id, Habit.type == HabitType.shower))
    workout = db.scalar(select(Habit).where(Habit.user_id == user.id, Habit.type == HabitType.workout))
    if shower and shower.last_done == today:
        score += 20
    if workout and workout.last_done == today:
        score += 20

    completed_today_count = len(
        list(db.scalars(select(Todo).where(Todo.user_id == user.id, Todo.completion_date == today)))
    )
    score += min(completed_today_count * 10, 30)

    screen_log = db.scalar(select(ScreenTimeLog).where(ScreenTimeLog.user_id == user.id, ScreenTimeLog.date == today))
    if screen_log and screen_log.hours <= SCREEN_TIME_LIMIT:
        score += 15

    social = db.scalar(select(SocialInteraction).where(SocialInteraction.user_id == user.id))
    if social and social.weekly_count <= SOCIAL_LIMIT:
        score += 15

    if score >= 95:
        grade = "SSS"
    elif score >= 90:
        grade = "SS"
    elif score >= 85:
        grade = "S"
    elif score >= 80:
        grade = "A+"
    elif score >= 75:
        grade = "A"
    elif score >= 70:
        grade = "A-"
    elif score >= 60:
        grade = "B"
    elif score >= 50:
        grade = "C"
    elif score >= 40:
        grade = "D"
    else:
        grade = "F"

    return score, grade


def finalize_daily_summary(db: Session, user: User) -> DailyScore:
    score, grade = calculate_daily_score(db, user)
    entry = DailyScore(user_id=user.id, date=date.today(), score=score, grade=grade)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry
