"""The daily tips: in the morning the one change that would raise your scores most today, in the
evening what's still open before midnight."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import QuestionnaireAttempt, User
from app.services import character_stats, daily_logs, profiles, streaks

# Short, concrete advice per part (the same wording as the apps' stat pages)
ADVICE = {
    "Sleep last night": "Aim for 7-9 hours tonight.",
    "Sleep debt (7 days)": "Pay back your sleep debt with an earlier night.",
    "Sleep regularity": "Fall asleep within 30 minutes of your usual time.",
    "Sleep quality": "No caffeine after 2 pm and no phone in the last hour before bed.",
    "Deep work": "Block 2-4 hours of focused work with notifications off.",
    "Physical activity": "A 30-minute brisk walk or 8,000 steps.",
    "Outdoors": "Get 20 minutes outside.",
    "Meditation": "10 minutes of meditation.",
    "Reels / Shorts / TikTok": "Keep reels under 15 minutes today.",
    "Passive video over 2h": "Cap videos and series at 2 hours.",
    "Gaming over 2h": "Cap gaming at 2 hours.",
    "Overwork today": "Stop before 10 hours of work and sleep instead.",
    "Overwork this week": "Ease off: past ~50 hours a week, extra hours stop paying off.",
    "Max push-up test": "Do a max push-up set and log it.",
    "Training consistency": "Fit in a strength session today.",
    "Steps (7-day avg)": "Walk 8,000-10,000 steps today.",
    "Cardio minutes / week": "Get 30 minutes of brisk activity.",
    "Calories on target": "Stay between 75% and 110% of your calorie target.",
    "Protein": "Hit your protein target today.",
    "Meals logged": "Log all three meals: snap a photo each time.",
    "Weight trend": "Weigh yourself and log it.",
    "Learning (28 days)": "Spend 30-60 minutes learning something.",
    "Daily check-ins": "Do the 30-second check-in tonight.",
    "Slept 7-9h": "Get 7-9 hours tonight.",
    "Showered": "Shower and tick it in the check-in.",
    "Tasks done on time": "Finish a quest before its deadline.",
    "Ate within calories": "Stay within your calorie target today.",
    "Social feeds": "Keep social feeds under 30 minutes.",
    "Unlocks": "Put the phone in another room while you work.",
    "Phone after midnight": "Phone away by midnight.",
    "Total screen time": "Keep phone time under 2-3 hours today.",
    "Meaningful contacts / week": "Call or meet someone for 30 minutes.",
    "Monthly income goal": "Log what you've earned this month.",
}


def _advice(part: str) -> str:
    return ADVICE.get(part) or ("Hit your daily push-up target." if part.endswith("push-ups") else f"Work on {part.lower()}.")


def _priority(db: Session, user: User) -> dict:
    """Weight per category from the latest questionnaire (6 for the most important), else all equal"""
    attempt = db.scalar(select(QuestionnaireAttempt).where(QuestionnaireAttempt.user_id == user.id)
                        .order_by(QuestionnaireAttempt.created_at.desc(), QuestionnaireAttempt.id.desc()).limit(1))
    order = attempt.answers.get("priorities", []) if attempt else []
    return {key: 6 - i for i, key in enumerate(order)}


def morning(db: Session, user: User, sheet: dict) -> dict:
    """The biggest gain available today, leaning toward the categories you said matter most"""
    weight = _priority(db, user)
    category_of = {code: key for key, _, codes in character_stats.CATEGORIES for code in codes}
    names = dict(character_stats.STATS)
    best = None
    for code, result in sheet["stats"].items():
        move = result.get("best_move")
        if move:
            value = move["points"] * weight.get(category_of.get(code), 3)
            if not best or value > best[0]:
                best = (value, code, move)
    if not best:
        return {"title": "💡 You're on track", "detail": "Nothing big to fix today. Keep your streaks going.", "stat": None, "points": 0}
    _, code, move = best
    return {
        "title": f"💡 {_advice(move['name'])}",
        "detail": f"Today's biggest gain: {move['name']} in {names[code]}, up to +{move['points']}.",
        "stat": code, "points": move["points"],
    }


def evening(db: Session, user: User) -> dict:
    """What's still open before midnight: a streak about to end, then today's targets, then bedtime"""
    state = streaks.streaks(db, user)
    at_risk = sorted((s for s in state["streaks"] if s["at_risk"]), key=lambda s: -s["current"])
    if at_risk:
        s = at_risk[0]
        return {"title": f"🔥 Your {s['current']}-day {s['name'].lower()} streak ends at midnight",
                "detail": f"Still to do today: {s['rule']}.", "stat": None, "points": 0}
    day = profiles.today(db, user)
    profile = profiles.get_profile(db, user)
    log = daily_logs.get_log(db, user, day)
    today = daily_logs.merged(log) if log else {}
    steps = today.get("body", {}).get("steps") or 0
    if steps < profile.steps_target:
        return {"title": f"👟 {profile.steps_target - steps:,} steps to go today",
                "detail": f"{steps:,} of your {profile.steps_target:,}. A 20-minute walk is about 2,500.", "stat": "STA", "points": 0}
    if not (log and log.manual):
        return {"title": "📝 Do your check-in", "detail": "30 seconds: sleep, work, learning, push-ups, people.", "stat": "DIS", "points": 0}
    return {"title": "😴 Wind down", "detail": "Phone away by midnight and aim for 7-9 hours of sleep.", "stat": "MP", "points": 0}
