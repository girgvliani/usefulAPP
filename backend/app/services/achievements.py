"""Achievements: badges earned from what the app can actually check, grouped into stories.

Every achievement is one number from your data (a "fact") reaching a target, so each one shows how to
get it and how far along you are. Nothing is self-reported beyond what the check-in already holds.
Earning one gives bonus XP (it counts toward your level) and sometimes a title you can wear.

Facts are worked out from history each time, so past days count: a marathon you ran before the app
existed is earned the first time the phone syncs it.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    EarnedAchievement, EpicMilestone, Friendship, Goal, Income, ProfilePhoto, Project, QuestionnaireAttempt, Todo, User,
)
from app.services import baby_steps, daily_logs, goals, profiles
from app.services.character_stats import calorie_ok

TIERS = {1: "Bronze", 2: "Silver", 3: "Gold", 4: "Legend"}


@dataclass(frozen=True)
class Story:
    key: str
    name: str
    icon: str
    blurb: str


@dataclass(frozen=True)
class Achievement:
    key: str
    story: str
    icon: str
    name: str
    how: str          # what to do, shown on every badge
    metric: str       # the fact it reads
    target: float     # earned once the fact reaches this
    unit: str         # for "6,300 / 10,000 steps"
    xp: int
    tier: int         # 1 bronze … 4 legend
    title: str | None = None  # a title you can wear once earned


STORIES = [
    Story("goggins", "Road to Jr. Goggins", "🏃", "Nobody is coming to save you. Start with one kilometre and don't stop at the finish line of your comfort zone."),
    Story("iron", "Iron Chest", "💪", "Push-ups: the oldest strength test there is. One rep at a time, then thousands."),
    Story("walker", "Ten Thousand Steps", "👟", "Every journey is mostly walking. Your phone counts every step."),
    Story("sleep", "Sleep Master", "😴", "The cheapest performance enhancer in the world is 7 to 9 hours a night."),
    Story("grind", "Stay Hard", "🔥", "Show up every day. The streak is the proof."),
    Story("monk", "Monk Mode", "🧘", "A quiet mind and a phone that doesn't own you."),
    Story("scholar", "The Scholar", "🧠", "Deep work and real learning, logged hour by hour."),
    Story("ramsey", "Ramsey's Way", "💰", "Dave Ramsey's Baby Steps, from the first $1,000 to building wealth and giving."),
    Story("fuel", "Fuel", "🍽️", "You can't out-train a bad diet. Log what you eat and stay within your calories."),
    Story("people", "Your People", "🤝", "Life is better with others. Friends in the app, and real time with people."),
    Story("adventurer", "The Adventurer", "🗺️", "Goals, quests, milestones and levels: the long game."),
    Story("firsts", "First Steps", "✨", "Getting to know the app, and yourself."),
]

A = Achievement
ACHIEVEMENTS = [
    # Running: Health Connect running workouts with their distance
    A("run_first", "goggins", "🏃", "First Run", "Go for a run of 1 km or more, recorded as a running workout in Samsung Health (or any app that shares with Health Connect).", "run_longest_km", 1, "km", 50, 1),
    A("run_5k", "goggins", "🎽", "5K", "Run 5 km in one go.", "run_longest_km", 5, "km", 100, 1),
    A("run_10k", "goggins", "🏅", "10K", "Run 10 km in one go.", "run_longest_km", 10, "km", 250, 2),
    A("run_half", "goggins", "🥈", "Half Marathon", "Run a half marathon: 21.1 km in one go.", "run_longest_km", 21, "km", 500, 3, "Half-Goggins"),
    A("run_marathon", "goggins", "👑", "Marathon", "Run a full marathon: 42.2 km in one go.", "run_longest_km", 42, "km", 1500, 4, "Jr. Goggins"),
    A("run_100", "goggins", "🛣️", "100 km Club", "Run 100 km in total.", "run_total_km", 100, "km", 300, 2),
    A("run_500", "goggins", "🌍", "Road Warrior", "Run 500 km in total.", "run_total_km", 500, "km", 1000, 4, "Road Warrior"),
    # Push-ups: the check-in and the camera counter
    A("push_first", "iron", "💪", "First Push", "Log push-ups on any day.", "pushups_best_day", 1, "push-ups", 25, 1),
    A("push_50", "iron", "🔩", "Fifty", "Do 50 push-ups in a day.", "pushups_best_day", 50, "push-ups", 75, 1),
    A("push_100", "iron", "⚙️", "Centurion", "Do 100 push-ups in a day.", "pushups_best_day", 100, "push-ups", 200, 2, "Centurion"),
    A("push_set_50", "iron", "🦾", "Fifty Straight", "Do 50 push-ups in one set (log it as your max in one set).", "pushups_max_set", 50, "in one set", 400, 3),
    A("push_1000", "iron", "🏋️", "Thousand", "Do 1,000 push-ups in total.", "pushups_total", 1000, "push-ups", 250, 2),
    A("push_10000", "iron", "🛡️", "Iron Chest", "Do 10,000 push-ups in total.", "pushups_total", 10000, "push-ups", 1000, 4, "Iron Chest"),
    A("cam_first", "iron", "📸", "Seen by the Machine", "Count a set with the camera rep counter in the phone app (☰ → Rep counter).", "camera_reps_total", 1, "reps", 50, 1),
    A("cam_100", "iron", "🤖", "Verified", "Have the camera count 100 push-ups in one day.", "camera_pushups_best_day", 100, "push-ups", 300, 3, "Verified"),
    A("squat_1000", "iron", "🦵", "Leg Day", "Do 1,000 squats in total (the camera counter logs them).", "squats_total", 1000, "squats", 300, 2),
    # Steps
    A("steps_10k", "walker", "👟", "Ten Thousand", "Walk 10,000 steps in a day.", "steps_best_day", 10000, "steps", 50, 1),
    A("steps_20k", "walker", "🥾", "Twenty Thousand", "Walk 20,000 steps in a day.", "steps_best_day", 20000, "steps", 150, 2),
    A("steps_30k", "walker", "🏔️", "Thirty Thousand", "Walk 30,000 steps in a day.", "steps_best_day", 30000, "steps", 400, 3),
    A("steps_week", "walker", "📅", "Week of Walking", "Walk 10,000 steps a day, 7 days in a row.", "steps_10k_streak", 7, "days in a row", 200, 2),
    A("steps_million", "walker", "🌐", "Millionaire Walker", "Walk 1,000,000 steps in total.", "steps_total", 1_000_000, "steps", 800, 4, "Wanderer"),
    # Sleep
    A("sleep_first", "sleep", "🌙", "Good Night", "Sleep 7-9 hours in a night.", "good_nights", 1, "nights", 25, 1),
    A("sleep_week", "sleep", "🛌", "Well Rested", "Sleep 7-9 hours, 7 nights in a row.", "good_sleep_streak", 7, "nights in a row", 200, 2, "Well Rested"),
    A("sleep_month", "sleep", "💤", "Dream Walker", "Sleep 7-9 hours, 30 nights in a row.", "good_sleep_streak", 30, "nights in a row", 700, 4, "Dream Walker"),
    A("sleep_100", "sleep", "🌌", "Hundred Nights", "Sleep 7-9 hours on 100 nights.", "good_nights", 100, "nights", 400, 3),
    # Check-in streaks
    A("checkin_first", "grind", "📝", "Day One", "Do your first check-in.", "checkin_days", 1, "check-ins", 25, 1),
    A("checkin_7", "grind", "🔥", "One Week", "Check in 7 days in a row.", "checkin_streak", 7, "days in a row", 100, 1),
    A("checkin_30", "grind", "⚔️", "Thirty Days", "Check in 30 days in a row.", "checkin_streak", 30, "days in a row", 400, 2, "Disciplined"),
    A("checkin_100", "grind", "🗿", "Unbreakable", "Check in 100 days in a row.", "checkin_streak", 100, "days in a row", 1000, 3, "Unbreakable"),
    A("checkin_365", "grind", "💀", "Stay Hard", "Check in 365 days in a row.", "checkin_streak", 365, "days in a row", 3000, 4, "Stays Hard"),
    # Mind and phone
    A("meditate_first", "monk", "🧘", "First Breath", "Meditate for 10 minutes or more.", "meditation_days", 1, "days", 25, 1),
    A("meditate_week", "monk", "🪷", "Still Week", "Meditate 10+ minutes a day, 7 days in a row.", "meditation_streak", 7, "days in a row", 200, 2),
    A("meditate_1000", "monk", "☯️", "Monk", "Meditate 1,000 minutes in total.", "meditation_total_min", 1000, "min", 500, 3, "Monk"),
    A("reels_zero", "monk", "📵", "Reels-Free Day", "A whole day with 0 minutes of Reels / Shorts / TikTok (measured by the phone).", "reels_free_days", 1, "days", 75, 1),
    A("reels_week", "monk", "🧊", "Unhooked", "Under 30 minutes of Reels / Shorts / TikTok, 7 days in a row.", "reels_under30_streak", 7, "days in a row", 300, 3, "Unhooked"),
    # Deep work and learning
    A("deep_4h", "scholar", "🎯", "In the Zone", "Log 4 hours of deep work in a day.", "deep_best_day_h", 4, "h", 100, 1),
    A("deep_100", "scholar", "🏛️", "Deep Worker", "Log 100 hours of deep work in total.", "deep_total_h", 100, "h", 500, 3, "Deep Worker"),
    A("learn_hour", "scholar", "📖", "Student", "Spend an hour learning in a day.", "learning_best_day_min", 60, "min", 50, 1),
    A("learn_100h", "scholar", "🎓", "Scholar", "Spend 100 hours learning in total.", "learning_total_min", 6000, "min", 600, 3, "Scholar"),
    # Money
    A("bs_1", "ramsey", "🐣", "Baby Step 1", "Save your starter emergency fund (Plan → Baby Steps).", "baby_step_1", 1, "", 150, 1),
    A("bs_2", "ramsey", "⛓️", "Debt Slayer", "Pay off every debt you listed, except the house.", "baby_step_2", 1, "", 600, 3, "Debt Slayer"),
    A("bs_3", "ramsey", "🏦", "Fully Funded", "Save 3-6 months of expenses.", "baby_step_3", 1, "", 500, 3),
    A("bs_7", "ramsey", "💎", "Ramsey Disciple", "Finish steps 1-6 that apply to you and give regularly: Baby Step 7.", "baby_step_7", 1, "", 1500, 4, "Ramsey Disciple"),
    A("income_goal", "ramsey", "💸", "Payday", "Reach your monthly income goal (Settings).", "income_goal_hit", 1, "", 200, 2),
    # Food
    A("meal_first", "fuel", "🍽️", "First Bite", "Log a meal (a photo works).", "meal_days", 1, "days", 25, 1),
    A("meals_week", "fuel", "🥗", "Logged Week", "Log 3+ meals a day, 7 days in a row.", "meals3_streak", 7, "days in a row", 200, 2),
    A("calories_week", "fuel", "⚖️", "On Target", "Log 3+ meals and stay within your calories, 7 days in a row.", "calories_streak", 7, "days in a row", 400, 3, "Clean Eater"),
    A("weight_5", "fuel", "📉", "Five Down", "Weigh 5 kg less than your first logged weight.", "weight_lost_kg", 5, "kg", 500, 3),
    # People
    A("friend_first", "people", "🤝", "Plus One", "Add your first friend (Friends).", "friends", 1, "friends", 50, 1),
    A("friends_5", "people", "👥", "Party of Five", "Have 5 friends in the app.", "friends", 5, "friends", 200, 2),
    A("social_week", "people", "💬", "Social Butterfly", "Spend 30+ minutes with someone, 7 days in a row.", "contact_streak", 7, "days in a row", 300, 3, "Social Butterfly"),
    # Long game
    A("goal_first", "adventurer", "🎯", "Goal Getter", "Reach one of your goals.", "goals_reached", 1, "goals", 100, 1),
    A("goals_5", "adventurer", "🏹", "Sharpshooter", "Reach 5 goals.", "goals_reached", 5, "goals", 400, 3),
    A("quests_10", "adventurer", "📜", "Questing", "Finish 10 quests.", "quests_done", 10, "quests", 100, 1),
    A("quests_100", "adventurer", "🗡️", "Quest Master", "Finish 100 quests.", "quests_done", 100, "quests", 600, 3, "Quest Master"),
    A("milestone_first", "adventurer", "🏔️", "Summit", "Complete an epic milestone.", "milestones_done", 1, "milestones", 200, 2),
    A("project_first", "adventurer", "💼", "Shipped", "Complete a paid project.", "projects_done", 1, "projects", 100, 1),
    A("level_10", "adventurer", "⭐", "Adept", "Reach level 10.", "level", 10, "LV", 150, 1),
    A("level_25", "adventurer", "🌟", "Veteran", "Reach level 25.", "level", 25, "LV", 400, 2),
    A("level_50", "adventurer", "💫", "Legend", "Reach level 50.", "level", 50, "LV", 1000, 4),
    # Firsts
    A("questionnaire", "firsts", "🧭", "Know Thyself", "Take the questionnaire.", "questionnaires", 1, "", 50, 1),
    A("photo", "firsts", "🖼️", "Face Reveal", "Add a profile photo (Profile & targets / Settings).", "has_photo", 1, "", 25, 1),
    A("customize", "firsts", "🎛️", "Tinkerer", "Turn a part of a stat off (Customize, LV 7).", "parts_off", 1, "", 25, 1),
    A("browsing", "firsts", "🌐", "Know Your Habits", "Import your Chrome history (website → Browsing).", "browser_days", 1, "days", 50, 1),
]
BY_KEY = {a.key: a for a in ACHIEVEMENTS}
TITLES = {a.key: a.title for a in ACHIEVEMENTS if a.title}


# ---- Facts


def _streak(days: dict[date, dict], test) -> int:
    """The longest run of consecutive days passing `test`"""
    best = run = 0
    previous = None
    for day in sorted(days):
        if test(days[day]):
            run = run + 1 if previous is not None and day - previous == timedelta(days=1) and run else 1
            best = max(best, run)
        else:
            run = 0
        previous = day
    return best


def facts(db: Session, user: User, level: int | None = None) -> dict:
    """Every number the achievements read. `level`: pass it when already known."""
    profile = profiles.get_profile(db, user)
    today = profiles.today(db, user)
    days: dict[date, dict] = {}
    checked_in: set[date] = set()
    for row in daily_logs.list_logs(db, user, date(2000, 1, 1), today):
        days[row.date] = daily_logs.merged(row)
        if row.manual:
            checked_in.add(row.date)

    def get(entry, section, key):
        value = entry.get(section, {}).get(key)
        return value if isinstance(value, (int, float)) and not isinstance(value, bool) else None

    def best(section, key):
        return max((get(e, section, key) or 0 for e in days.values()), default=0)

    def total(section, key):
        return sum(get(e, section, key) or 0 for e in days.values())

    def sleep_ok(e):
        hours = get(e, 'sleep', 'hours')
        return hours is not None and 7 <= hours <= 9

    def reels(e):
        return get(e, 'screen', 'short_video_min')

    meals = {date.fromisoformat(d): v for d, v in daily_logs.meal_totals(db, user, date(2000, 1, 1), today).items()}
    calories = daily_logs.nutrition_targets(db, user, today)['calories']
    weights = [w for _, w in sorted((d, get(e, 'body', 'weight_kg')) for d, e in days.items()) if w]

    plan = baby_steps.steps(profile.baby_steps)
    step_done = {s['step']: s['done'] and s['progress'] != "n/a" for s in plan['steps']}
    listed_debts = [d for d in baby_steps.plan_of(profile.baby_steps)['debts'] if (d.get('original') or 0) > 0]
    started = plan['score'] is not None
    income = db.scalar(select(Income).where(Income.user_id == user.id))
    data = daily_logs.stats_input(db, user, today)
    reached = sum(
        1 for goal in db.scalars(select(Goal).where(Goal.user_id == user.id))
        if goals.progress(goal.start_value, goal.target_value, goals.current_value(goal, data, today.isoformat())) == 1
    )

    def count(model, *where):
        return db.scalar(select(func.count()).select_from(model).where(*where)) or 0

    if level is None:
        from app.services import levels
        level = levels.summary(db, user)['level']

    return {
        'run_longest_km': best('body', 'longest_run_km'),
        'run_total_km': total('body', 'run_km'),
        'pushups_best_day': best('body', 'pushups'),
        'pushups_total': total('body', 'pushups'),
        'pushups_max_set': max(best('body', 'max_pushups'), best('body', 'cam_best_set')),
        'camera_reps_total': total('body', 'cam_pushups') + total('body', 'cam_squats') + total('body', 'cam_situps'),
        'camera_pushups_best_day': best('body', 'cam_pushups'),
        'squats_total': total('body', 'squats'),
        'steps_best_day': best('body', 'steps'),
        'steps_total': total('body', 'steps'),
        'steps_10k_streak': _streak(days, lambda e: (get(e, 'body', 'steps') or 0) >= 10000),
        'good_nights': sum(1 for e in days.values() if sleep_ok(e)),
        'good_sleep_streak': _streak(days, sleep_ok),
        'checkin_days': len(checked_in),
        'checkin_streak': _streak({d: {} for d in checked_in}, lambda e: True),
        'meditation_days': sum(1 for e in days.values() if (get(e, 'mind', 'meditation_min') or 0) >= 10),
        'meditation_streak': _streak(days, lambda e: (get(e, 'mind', 'meditation_min') or 0) >= 10),
        'meditation_total_min': total('mind', 'meditation_min'),
        'reels_free_days': sum(1 for e in days.values() if reels(e) == 0),
        'reels_under30_streak': _streak(days, lambda e: reels(e) is not None and reels(e) < 30),
        'deep_best_day_h': best('work', 'deep'),
        'deep_total_h': total('work', 'deep'),
        'learning_best_day_min': best('mind', 'learning_min'),
        'learning_total_min': total('mind', 'learning_min'),
        'baby_step_1': int(started and step_done[1]),
        'baby_step_2': int(bool(listed_debts) and step_done[2]),  # had debts and paid them all
        'baby_step_3': int(started and step_done[1] and step_done[2] and step_done[3]),
        'baby_step_7': int(started and plan['current'] is None),
        'income_goal_hit': int(bool(income and income.monthly_goal and income.current_month_earnings >= income.monthly_goal)),
        'meal_days': len(meals),
        'meals3_streak': _streak(meals, lambda m: m['count'] >= 3),
        'calories_streak': _streak(meals, lambda m: m['count'] >= 3 and calorie_ok(m['kcal'], calories)),
        'weight_lost_kg': round(weights[0] - min(weights), 1) if weights else 0,
        'friends': len([1 for _ in db.scalars(select(Friendship.id).where(
            Friendship.status == "accepted", (Friendship.requester_id == user.id) | (Friendship.addressee_id == user.id)))]),
        'contact_streak': _streak(days, lambda e: (get(e, 'social', 'interactions') or 0) >= 1),
        'goals_reached': reached,
        'quests_done': count(Todo, Todo.user_id == user.id, Todo.completed.is_(True)),
        'milestones_done': count(EpicMilestone, EpicMilestone.user_id == user.id, EpicMilestone.completed.is_(True)),
        'projects_done': count(Project, Project.user_id == user.id, Project.completed.is_(True)),
        'level': level,
        'questionnaires': count(QuestionnaireAttempt, QuestionnaireAttempt.user_id == user.id),
        'has_photo': count(ProfilePhoto, ProfilePhoto.user_id == user.id),
        'parts_off': int(any((profile.customization or {}).get('off', {}).values())),
        'browser_days': sum(1 for e in days.values() if e.get('browser')),
    }


# ---- Earning


def earned_rows(db: Session, user: User) -> dict[str, datetime]:
    rows = db.scalars(select(EarnedAchievement).where(EarnedAchievement.user_id == user.id))
    return {r.key: r.earned_at for r in rows if r.key in BY_KEY}


def xp_earned(db: Session, user: User) -> int:
    """Bonus XP from every achievement earned (levels.summary adds it)"""
    return sum(BY_KEY[key].xp for key in earned_rows(db, user))


def evaluate(db: Session, user: User) -> list[Achievement]:
    """Saves every achievement newly reached and returns them. Run for the signed-in user only."""
    from app.services import levels
    have = earned_rows(db, user)
    found_all: list[Achievement] = []
    values = None
    for _ in range(4):  # earning XP can lift the level, which can earn a level badge
        level = levels.summary(db, user)['level']
        values = facts(db, user, level) if values is None else {**values, 'level': level}
        found = [a for a in ACHIEVEMENTS if a.key not in have and values.get(a.metric, 0) >= a.target]
        if not found:
            break
        now = datetime.now(timezone.utc)
        for a in found:
            db.add(EarnedAchievement(user_id=user.id, key=a.key, earned_at=now))
            have[a.key] = now
        db.commit()
        found_all += found
    return found_all


def brief(a: Achievement) -> dict:
    return {"key": a.key, "story": a.story, "icon": a.icon, "name": a.name, "tier": a.tier, "xp": a.xp, "title": a.title}


def unseen(db: Session, user: User) -> list[dict]:
    """Earned since the user last saw the unlock screen, oldest first"""
    seen = profiles.get_profile(db, user).achievements_seen_at
    rows = sorted(earned_rows(db, user).items(), key=lambda kv: kv[1])
    return [brief(BY_KEY[key]) for key, at in rows if seen is None or _aware(at) > _aware(seen)]


def _aware(at: datetime) -> datetime:
    return at if at.tzinfo else at.replace(tzinfo=timezone.utc)


def mark_seen(db: Session, user: User) -> None:
    profiles.get_profile(db, user).achievements_seen_at = datetime.now(timezone.utc)
    db.commit()


def worn_title(db: Session, user: User) -> str | None:
    key = profiles.get_profile(db, user).title_key
    return TITLES.get(key) if key and key in earned_rows(db, user) else None


def wear(db: Session, user: User, key: str | None) -> None:
    if key is not None:
        if key not in TITLES:
            raise ValueError("That achievement has no title")
        if key not in earned_rows(db, user):
            raise ValueError("Earn it first")
    profiles.get_profile(db, user).title_key = key
    db.commit()


def overview(db: Session, user: User) -> dict:
    """Every achievement with how to get it and your progress, grouped into stories"""
    have = earned_rows(db, user)
    values = facts(db, user)
    items = []
    for a in ACHIEVEMENTS:
        value = values.get(a.metric, 0)
        items.append({
            **brief(a), "how": a.how, "tier_name": TIERS[a.tier], "unit": a.unit,
            "value": round(value, 1) if isinstance(value, float) else value, "target": a.target,
            "progress": 1.0 if a.key in have else round(min(1.0, value / a.target), 3),
            "earned_at": have.get(a.key),
        })
    stories = []
    for s in STORIES:
        chapters = [a.key for a in ACHIEVEMENTS if a.story == s.key]
        stories.append({
            "key": s.key, "name": s.name, "icon": s.icon, "blurb": s.blurb, "chapters": chapters,
            "done": sum(1 for k in chapters if k in have),
            "next": next((k for k in chapters if k not in have), None),
        })
    return {
        "earned": len(have), "total": len(ACHIEVEMENTS), "xp": sum(BY_KEY[k].xp for k in have),
        "title": profiles.get_profile(db, user).title_key if worn_title(db, user) else None,
        "stories": stories, "achievements": items,
    }


def showcase(db: Session, user: User, limit: int = 8) -> dict:
    """What friends see when the achievements switch is on: the count and the latest badges"""
    have = earned_rows(db, user)
    latest = sorted(have.items(), key=lambda kv: _aware(kv[1]), reverse=True)[:limit]
    return {"earned": len(have), "total": len(ACHIEVEMENTS),
            "badges": [{"key": k, "icon": BY_KEY[k].icon, "name": BY_KEY[k].name, "tier": BY_KEY[k].tier} for k, _ in latest]}
