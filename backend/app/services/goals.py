"""Goal progress. Built-in goal types read their current value from the user's logs;
custom goals store it on the goal."""

from statistics import mean

from app.models import Goal, GoalType
from app.services.character_stats import values, window

UNITS = {
    GoalType.weight: "kg",
    GoalType.max_pushups: "reps",
    GoalType.steps: "steps/day",
    GoalType.sleep: "h/night",
}
LABELS = {
    GoalType.weight: "Weight",
    GoalType.max_pushups: "Max push-ups",
    GoalType.steps: "Daily steps",
    GoalType.sleep: "Sleep",
    GoalType.income: "Monthly income",
    GoalType.custom: "Goal",
}


def unit_for(goal_type: GoalType, currency: str) -> str:
    return currency if goal_type == GoalType.income else UNITS.get(goal_type, "")


def current_value(goal: Goal, data: dict, day: str) -> float | None:
    """Today's value for the goal. `data` is daily_logs.stats_input for `day`."""
    logs = data['daily_logs']
    if goal.type == GoalType.weight:
        weights = values(window(logs, day, 60), 'body', 'weight_kg')
        return weights[-1] if weights else None
    if goal.type == GoalType.max_pushups:
        tests = values(window(logs, day, 60), 'body', 'max_pushups')
        return tests[-1] if tests else None
    if goal.type == GoalType.steps:
        steps = values(window(logs, day, 7), 'body', 'steps')
        return round(mean(steps)) if steps else None
    if goal.type == GoalType.sleep:
        nights = values(window(logs, day, 7), 'sleep', 'hours')
        return round(mean(nights), 2) if nights else None
    if goal.type == GoalType.income:
        return data['income']['current_month_earnings']
    return goal.current_value


def progress(start: float, target: float, current: float | None) -> float | None:
    """0 at the start, 1 at the target, whichever way the target lies (losing or gaining)."""
    if current is None:
        return None
    return round(min(1.0, max(0.0, (current - start) / (target - start))), 3)
