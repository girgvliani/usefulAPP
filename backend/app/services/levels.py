"""Global level: every XP source in one number. Worked out from history each time, so nothing is ever
counted twice and past days count too.

XP = quest XP (life areas: todos, projects, milestones, habits) + daily activity XP (below)
     + GOAL_XP per goal reached.
Levels get steadily longer: reaching level L takes 50·L·(L+1) XP (L1 100, L2 300, L5 1,500, L10 5,500).
"""

from datetime import date, timedelta
from math import floor, sqrt

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Goal, LifeArea, User
from app.services import daily_logs, goals, profiles
from app.services.character_stats import calorie_ok

GOAL_XP = 250
LEVEL_STEP = 50
HISTORY_DAYS = 30
# (from level, title): a new title every few levels
TITLES = [(0, "Novice"), (5, "Apprentice"), (10, "Adept"), (15, "Veteran"), (20, "Elite"), (30, "Master"),
          (40, "Grandmaster"), (50, "Legend"), (1000, "Genius")]


def title_for(level: int) -> str:
    return [name for start, name in TITLES if level >= start][-1]


def xp_for_level(level: int) -> int:
    return LEVEL_STEP * level * (level + 1)


def level_for(xp: float) -> int:
    return floor((sqrt(1 + 4 * xp / LEVEL_STEP) - 1) / 2)


def day_xp(entry: dict, meals: dict | None, targets: dict) -> list[tuple[str, int]]:
    """(reason, XP) for one day's logs and meals."""
    def get(section, key):
        return entry.get(section, {}).get(key)

    earned = []
    if entry.get('_checked_in'):
        earned.append(("Check-in", 20))
    hours = get('sleep', 'hours')
    if hours is not None and 7 <= hours <= 9:
        earned.append(("Slept 7-9h", 15))
    if (get('body', 'pushups') or 0) >= targets['pushups']:
        earned.append(("Push-up target", 15))
    if (get('body', 'steps') or 0) >= targets['steps']:
        earned.append(("Step target", 15))
    if deep := get('work', 'deep'):
        earned.append(("Deep work", min(40, round(10 * deep))))
    if learning := get('mind', 'learning_min'):
        earned.append(("Learning", min(30, learning // 3)))
    if (get('mind', 'meditation_min') or 0) >= 10:
        earned.append(("Meditation", 5))
    if get('body', 'shower'):
        earned.append(("Shower", 5))
    reels = get('screen', 'short_video_min')
    if reels is not None and reels <= 30:
        earned.append(("Reels under 30 min", 10))
    if contacts := get('social', 'interactions'):
        earned.append(("Social contact", min(20, 10 * contacts)))
    if meals:
        earned.append(("Meals logged", 5 * min(3, meals['count'])))
        if meals['count'] >= 3 and calorie_ok(meals['kcal'], targets['calories']):
            earned.append(("Within calories", 15))
    return [(reason, xp) for reason, xp in earned if xp > 0]


def summary(db: Session, user: User) -> dict:
    today = profiles.today(db, user)
    profile = profiles.get_profile(db, user)
    rows = daily_logs.list_logs(db, user, date(2000, 1, 1), today)
    meals = daily_logs.meal_totals(db, user, date(2000, 1, 1), today)
    targets = {
        'pushups': profile.pushup_target,
        'steps': profile.steps_target,
        'calories': daily_logs.nutrition_targets(db, user, today)['calories'],
    }

    days = {row.date.isoformat(): {**daily_logs.merged(row), '_checked_in': bool(row.manual)} for row in rows}
    activity = 0
    per_day: dict[str, int] = {}
    today_items: list[tuple[str, int]] = []
    for day in sorted(set(days) | set(meals)):
        items = day_xp(days.get(day, {}), meals.get(day), targets)
        per_day[day] = sum(xp for _, xp in items)
        activity += per_day[day]
        if day == today.isoformat():
            today_items = items
    history = [
        {'date': d, 'xp': per_day.get(d, 0)}
        for d in ((today - timedelta(days=back)).isoformat() for back in range(HISTORY_DAYS - 1, -1, -1))
    ]

    quests = db.scalar(select(func.coalesce(func.sum(LifeArea.xp), 0)).where(LifeArea.user_id == user.id)) or 0
    data = daily_logs.stats_input(db, user, today)
    reached = sum(
        1 for goal in db.scalars(select(Goal).where(Goal.user_id == user.id))
        if goals.progress(goal.start_value, goal.target_value, goals.current_value(goal, data, today.isoformat())) == 1
    )

    xp = activity + quests + GOAL_XP * reached
    level = level_for(xp)
    return {
        'level': level,
        'title': title_for(level),
        'next_title': next((f"{name} at LV {start}" for start, name in TITLES if start > level), None),
        'xp': xp,
        'level_start_xp': xp_for_level(level),
        'next_level_xp': xp_for_level(level + 1),
        'today_xp': sum(value for _, value in today_items),
        'today': [{'reason': reason, 'xp': value} for reason, value in today_items],
        'sources': {'activity': activity, 'quests': quests, 'goals': GOAL_XP * reached},
        'history': history,
    }
