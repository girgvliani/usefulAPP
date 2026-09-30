"""Streaks: days in a row of doing something, counted back from today, or from yesterday while today is
still open. A streak you haven't kept today is "at risk" (it breaks at midnight), unless today already
went over a limit (too many reels, a short night): then it's "broken today" and can't be saved."""

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import PushupLog, User
from app.services import daily_logs, profiles
from app.services.character_stats import CALORIE_BAND, MEALS_A_DAY, calorie_ok

LOOKBACK_DAYS = 400
ANGRY_FROM_HOUR = 18  # an unkept streak turns from worried to angry in the evening
LEARNING_MIN = 15
REELS_LIMIT = 30


def _current(days: set[date], today: date) -> tuple[int, bool]:
    done_today = today in days
    day = today if done_today else today - timedelta(days=1)
    count = 0
    while day in days:
        count += 1
        day -= timedelta(days=1)
    return count, done_today


def _best(days: set[date]) -> int:
    best = run = 0
    previous = None
    for day in sorted(days):
        run = run + 1 if previous and (day - previous).days == 1 else 1
        best = max(best, run)
        previous = day
    return best


def _field(entry: dict, section: str, key: str):
    return entry.get(section, {}).get(key)


def streaks(db: Session, user: User) -> dict:
    today = profiles.today(db, user)
    hour = profiles.now(db, user).hour
    profile = profiles.get_profile(db, user)
    since = today - timedelta(days=LOOKBACK_DAYS)

    rows = daily_logs.list_logs(db, user, since, today)
    logs = {row.date: daily_logs.merged(row) for row in rows}
    checked_in = {row.date for row in rows if row.manual}
    pushups: dict[date, int] = {}
    for log in db.scalars(select(PushupLog).where(PushupLog.user_id == user.id, PushupLog.date >= since)):
        pushups[log.date] = max(pushups.get(log.date, 0), log.count)
    for day, entry in logs.items():
        if (count := _field(entry, 'body', 'pushups')) is not None:
            pushups[day] = max(pushups.get(day, 0), count)

    meals = daily_logs.meal_totals(db, user, since, today)
    calories = daily_logs.nutrition_targets(db, user, today)['calories']
    ate = {date.fromisoformat(day): totals for day, totals in meals.items()}

    def days(test) -> set[date]:
        return {day for day, entry in logs.items() if test(entry)}

    def between(section, key, low, high):
        return lambda e: (v := _field(e, section, key)) is not None and low <= v <= high

    def outside(section, key, low, high):
        """Logged, and out of range: for limits, that day is lost whatever happens later."""
        return days(lambda e: (v := _field(e, section, key)) is not None and not low <= v <= high)

    # (key, name, emoji, rule, days kept, days already lost)
    rules = [
        ('checkin', 'Check-in', '📝', 'filled in the check-in', checked_in, set()),
        ('pushups', 'Push-ups', '💪', f'{profile.pushup_target}+ push-ups',
         {day for day, count in pushups.items() if count >= profile.pushup_target}, set()),
        ('sleep', 'Sleep', '😴', '7-9h of sleep', days(between('sleep', 'hours', 7, 9)), outside('sleep', 'hours', 7, 9)),
        ('focus', 'Focus', '📵', f'reels under {REELS_LIMIT} min', days(between('screen', 'short_video_min', 0, REELS_LIMIT)),
         outside('screen', 'short_video_min', 0, REELS_LIMIT)),
        ('steps', 'Steps', '👟', f'{profile.steps_target:,}+ steps', days(between('body', 'steps', profile.steps_target, 10**9)), set()),
        ('learning', 'Learning', '📚', f'{LEARNING_MIN}+ min learning', days(between('mind', 'learning_min', LEARNING_MIN, 1440)), set()),
        ('shower', 'Shower', '🚿', 'showered', days(lambda e: _field(e, 'body', 'shower') is True), set()),
        ('meals', 'Meals', '🍽️', f'{MEALS_A_DAY} meals logged', {d for d, t in ate.items() if t['count'] >= MEALS_A_DAY}, set()),
    ]
    if calories:
        # A day counts once it's fully logged and in range; going over the top ends it for the day
        rules.append(('calories', 'Calories', '🎯', f'within ~{calories} kcal',
                      {d for d, t in ate.items() if t['count'] >= MEALS_A_DAY and calorie_ok(t['kcal'], calories)},
                      {d for d, t in ate.items() if t['kcal'] > CALORIE_BAND[1] * calories}))
    result = []
    for key, name, emoji, rule, kept, lost in rules:
        current, done_today = _current(kept, today)
        broken_today = current > 0 and not done_today and today in lost
        result.append({
            'key': key, 'name': name, 'emoji': emoji, 'rule': rule,
            'current': current, 'best': max(_best(kept), current),
            'done_today': done_today, 'at_risk': current > 0 and not done_today and not broken_today,
            'broken_today': broken_today,
        })

    longest_first = lambda group: sorted(group, key=lambda s: -s['current'])
    at_risk = longest_first(s for s in result if s['at_risk'])
    broken = longest_first(s for s in result if s['broken_today'])
    active = [s for s in result if s['current'] > 0]
    if at_risk:
        top = at_risk[0]
        mood = 'angry' if hour >= ANGRY_FROM_HOUR else 'worried'
        message = f"Your {top['current']}-day {top['name'].lower()} streak dies at midnight."
    elif broken:
        top = broken[0]
        mood, message = 'angry', f"You broke your {top['current']}-day {top['name'].lower()} streak today."
    elif active:
        mood, message = 'happy', 'Every streak is safe today. Stay hard.'
    else:
        mood, message = 'idle', 'No streaks yet. Start one today.'
    return {'date': today, 'mood': mood, 'message': message, 'streaks': result}
