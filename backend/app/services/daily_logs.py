"""Daily logs: storing phone syncs and check-ins, and shaping them for character_stats."""

from datetime import date, timedelta
from statistics import mean

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DailyLog, Goal, GoalType, Income, Meal, PushupLog, Todo, User
from app.services import nutrition, profiles
from app.services.character_stats import values, window


def merge_sections(base: dict, updates: dict) -> dict:
    """{section: {field: value}} merge; fields in `updates` win, everything else is kept."""
    merged = {section: dict(fields) for section, fields in base.items()}
    for section, fields in updates.items():
        merged[section] = {**merged.get(section, {}), **fields}
    return merged


def merged(log: DailyLog) -> dict:
    return merge_sections(log.auto or {}, log.manual or {})


def get_log(db: Session, user: User, day: date) -> DailyLog | None:
    return db.scalar(select(DailyLog).where(DailyLog.user_id == user.id, DailyLog.date == day))


def save(db: Session, user: User, day: date, source: str, updates: dict) -> DailyLog:
    """Merge `updates` into the day's `source` column, creating the row if needed."""
    log = get_log(db, user, day)
    if log is None:
        log = DailyLog(user_id=user.id, date=day, auto={}, manual={})
        db.add(log)
    # Assign a new dict so SQLAlchemy notices the JSON change
    setattr(log, source, merge_sections(getattr(log, source) or {}, updates))
    db.commit()
    db.refresh(log)
    return log


def clear(db: Session, user: User, day: date, sources: tuple[str, ...], section: str | None, field: str | None) -> bool:
    """Remove a whole source, one section, or one field from a day. Deletes the row once both
    sources are empty. Returns False if nothing was logged that day."""
    log = get_log(db, user, day)
    if log is None:
        return False
    for source in sources:
        data = {name: dict(fields) for name, fields in (getattr(log, source) or {}).items()}
        if section is None:
            data = {}
        elif field is None:
            data.pop(section, None)
        elif section in data:
            data[section].pop(field, None)
            if not data[section]:
                data.pop(section)
        setattr(log, source, data)
    if not log.auto and not log.manual:
        db.delete(log)
    db.commit()
    return True


def list_logs(db: Session, user: User, start: date, end: date) -> list[DailyLog]:
    return list(db.scalars(
        select(DailyLog)
        .where(DailyLog.user_id == user.id, DailyLog.date >= start, DailyLog.date <= end)
        .order_by(DailyLog.date)
    ))


def weight_direction(db: Session, user: User) -> str | None:
    """"decrease" / "increase" from the newest weight goal, or None to maintain."""
    goal = db.scalar(
        select(Goal).where(Goal.user_id == user.id, Goal.type == GoalType.weight).order_by(Goal.created_at.desc())
    )
    if goal is None:
        return None
    return "decrease" if goal.target_value < goal.start_value else "increase"


def nutrition_targets(db: Session, user: User, day: date, logs: dict | None = None) -> dict:
    """Calorie and protein targets for `day`, from the profile, the latest weight, the week's steps and
    the weight goal. `logs` (merged, by ISO date) saves a second load when the caller has them."""
    if logs is None:
        logs = {log.date.isoformat(): merged(log) for log in list_logs(db, user, day - timedelta(days=60), day)}
    weights = values(window(logs, day.isoformat(), 60), 'body', 'weight_kg')
    steps = values(window(logs, day.isoformat(), 7), 'body', 'steps')
    return nutrition.targets(
        profiles.get_profile(db, user), weights[-1] if weights else None, mean(steps) if steps else None,
        weight_direction(db, user), day,
    )


def meal_totals(db: Session, user: User, since: date, until: date) -> dict:
    """{ISO date: {kcal, protein, count}} for days with meals."""
    per_day: dict = {}
    for meal in db.scalars(select(Meal).where(Meal.user_id == user.id, Meal.date >= since, Meal.date <= until)):
        day = per_day.setdefault(meal.date.isoformat(), {'kcal': 0.0, 'protein': 0.0, 'count': 0})
        day['kcal'] += meal.kcal
        day['protein'] += meal.protein
        day['count'] += 1
    return per_day


def stats_input(db: Session, user: User, day: date, start: date | None = None) -> dict:
    """The data shape character_stats expects (the terminal app's JSON), built from the database.
    Pass `start` to cover every day from `start` to `day` in one load (stat history)."""
    since = (start or day) - timedelta(days=60)  # longest window any stat looks at
    logs = list_logs(db, user, since, day)
    pushups = db.scalars(select(PushupLog).where(PushupLog.user_id == user.id, PushupLog.date >= since))
    todos = db.scalars(select(Todo).where(Todo.user_id == user.id, Todo.deadline >= since))
    income = db.scalar(select(Income).where(Income.user_id == user.id))
    merged_logs = {log.date.isoformat(): merged(log) for log in logs}
    targets = nutrition_targets(db, user, day, merged_logs)
    return {
        'daily_logs': merged_logs,
        'meals': meal_totals(db, user, since, day),
        'nutrition': {
            'calories': targets['calories'], 'protein': targets['protein'], 'direction': weight_direction(db, user),
            'missing': targets['missing'],
        },
        'habits': {'workout': {'pushup_history': [{'date': p.date.isoformat(), 'count': p.count} for p in pushups]}},
        'todos': [
            {
                'deadline': t.deadline.isoformat(),
                'completed': t.completed,
                'completion_date': t.completion_date.isoformat() if t.completion_date else None,
            }
            for t in todos
        ],
        'income': {
            'monthly_goal': income.monthly_goal if income else 0,
            'current_month_earnings': income.current_month_earnings if income else 0,
            'currency': profiles.get_profile(db, user).currency,
        },
    }
