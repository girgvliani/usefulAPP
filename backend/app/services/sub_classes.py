"""Sub-classes: each person's own stats inside the six classes (docs: usefulAPP-expo/docs/PATHS-DESIGN.md).

The six classes are the same for everyone. Inside them, the nine standard stats are the built-in
sub-classes (a person can hide any of them) and people add their own. A custom sub-class has one
measure:

- number: a value typed in the check-in, with a target per day or per week, more or less being better
- yesno: done or not in the check-in; per week it counts the days ("3 times a week")
- rating: a 1-5 self-rating in the check-in (marked as self-rated)
- field: a value the app already has in the day log (steps, learning minutes, reels…)

It scores 0-100 like the standard stats: the last 14 days against the target (the last 7 for weekly
targets). Days without a value are left out, so a missing day never counts as zero. The standard
stats used for comparisons with friends skip all of this.
"""
from datetime import timedelta
from statistics import mean

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import SubClass, User
from app.services import character_stats, log_fields, profiles

CLASS_KEYS = [key for key, _, _ in character_stats.CATEGORIES]
KINDS = ("number", "yesno", "rating", "field")
MAX_CUSTOM = 40
WINDOW_DAYS = 14
WEEK_DAYS = 7


def code_of(sub: SubClass) -> str:
    return f"c{sub.id}"


def data_fields() -> list[dict]:
    """Day-log values a sub-class can read (kind field): numbers and yes/no, not times of day"""
    return [
        {"field": f"{section}.{key}", "label": label, "unit": unit, "kind": kind}
        for section, key, label, unit, kind, _source, _feeds in log_fields.FIELDS
        if kind in ("decimal", "whole", "yesno")
    ]


FIELD_KEYS = {f["field"] for f in data_fields()}


def custom_subs(db: Session, user: User, active_only: bool = False) -> list[SubClass]:
    query = select(SubClass).where(SubClass.user_id == user.id)
    if active_only:
        query = query.where(SubClass.active)
    return list(db.scalars(query.order_by(SubClass.class_key, SubClass.position, SubClass.id)))


def hidden_builtins(db: Session, user: User) -> list[str]:
    return list((profiles.get_profile(db, user).customization or {}).get("hidden", []))


def value_of(entry: dict, sub: SubClass):
    if sub.kind == "field":
        section, key = sub.field.split(".", 1)
        return entry.get(section, {}).get(key)
    return entry.get("custom", {}).get(str(sub.id))


def day_score(sub: SubClass, value) -> float | None:
    """0-1 for one day's value"""
    if value is None:
        return None
    if sub.kind == "rating":
        return max(0.0, min(1.0, (float(value) - 1) / 4))
    if isinstance(value, bool) or sub.kind == "yesno":
        return 1.0 if bool(value) == (sub.better == "more") else 0.0
    return against_target(float(value), sub.target, sub.better)


def against_target(value: float, target: float | None, better: str) -> float | None:
    if not target:
        return None
    if better == "more":
        return max(0.0, min(1.0, value / target))
    return 1.0 if value <= target else max(0.0, 1 - (value - target) / target)


def _fmt(n: float) -> str:
    return f"{n:g}" if n == int(n) else f"{n:.1f}"


def score(sub: SubClass, logs: dict, day: str) -> dict:
    """The sub-class's result in the same shape as a standard stat (character_stats.combine)"""
    unit = f" {sub.unit}" if sub.unit else ""
    if sub.period == "week" and sub.kind != "rating":
        dates = character_stats.last_dates(day, WEEK_DAYS)
        values = [value_of(logs.get(d, {}), sub) for d in dates]
        values = [v for v in values if v is not None]
        if not values:
            result_score, note = None, "nothing logged this week"
        elif sub.kind == "yesno" or all(isinstance(v, bool) for v in values):
            done = sum(1 for v in values if bool(v) == (sub.better == "more"))
            result_score = against_target(done, sub.target, "more")
            note = f"{done} of {_fmt(sub.target or 0)} times this week"
        else:
            total = sum(float(v) for v in values)
            result_score = against_target(total, sub.target, sub.better)
            note = f"{_fmt(total)}{unit} this week, target {'≤' if sub.better == 'less' else ''}{_fmt(sub.target or 0)}{unit}"
    else:
        dates = character_stats.last_dates(day, WINDOW_DAYS)
        scored = [(d, day_score(sub, value_of(logs.get(d, {}), sub))) for d in dates]
        known = [s for _, s in scored if s is not None]
        if not known:
            result_score, note = None, "not logged in the last 2 weeks"
        else:
            result_score = mean(known)
            if sub.kind == "rating":
                note = f"average {_fmt(1 + 4 * result_score)}/5 over {len(known)} days"
            else:
                hit = sum(1 for s in known if s >= 0.999)
                note = f"on target {hit} of {len(known)} logged days"
    result = character_stats.combine([character_stats.component(sub.name, 1, result_score, note)])
    result.update(custom=True, self_rated=sub.kind == "rating", icon=sub.icon)
    return result


def personal_sheet(sheet: dict, subs: list[SubClass], hidden: list[str], logs: dict, day: str) -> dict:
    """Adds a person's own sub-classes to their character sheet and rebuilds the classes from what they
    keep: hidden built-in stats leave their class, custom ones join theirs. Adds `layout` (class →
    codes in order) and `names` (code → name) for whoever shows it."""
    names = dict(character_stats.STATS)
    for sub in subs:
        if sub.active:
            sheet["stats"][code_of(sub)] = score(sub, logs, day)
            names[code_of(sub)] = sub.name
    layout = {
        key: [c for c in codes if c not in hidden] + [code_of(s) for s in subs if s.active and s.class_key == key]
        for key, _, codes in character_stats.CATEGORIES
    }
    categories = character_stats.category_scores({c: r["score"] for c, r in sheet["stats"].items()}, layout)
    known = [s for s in categories.values() if s is not None]
    sheet.update(categories=categories, overall=round(mean(known)) if known else None, layout=layout, names=names)
    return sheet


def view(db: Session, user: User) -> dict:
    """The six classes with every sub-class, built-in and custom, for the editor"""
    hidden = hidden_builtins(db, user)
    subs = custom_subs(db, user)
    classes = []
    for key, name, codes in character_stats.CATEGORIES:
        builtin = [{"code": c, "name": dict(character_stats.STATS)[c], "builtin": True, "active": c not in hidden} for c in codes]
        own = [describe(s) for s in subs if s.class_key == key]
        classes.append({"key": key, "name": name, "sub_classes": builtin + own})
    return {"classes": classes, "fields": data_fields(), "max_custom": MAX_CUSTOM, "custom_count": len(subs)}


def describe(sub: SubClass) -> dict:
    return {
        "id": sub.id, "code": code_of(sub), "builtin": False, "class_key": sub.class_key, "name": sub.name,
        "icon": sub.icon, "kind": sub.kind, "field": sub.field, "unit": sub.unit, "target": sub.target,
        "period": sub.period, "better": sub.better, "active": sub.active, "self_rated": sub.kind == "rating",
        "path_key": sub.path_key,
    }


def check(values: dict) -> None:
    """Raises ValueError when a sub-class's settings don't fit together"""
    kind = values["kind"]
    if values["class_key"] not in CLASS_KEYS:
        raise ValueError("Unknown class")
    if kind not in KINDS:
        raise ValueError("Unknown kind of measure")
    if kind == "field" and values.get("field") not in FIELD_KEYS:
        raise ValueError("Pick a value the app already has")
    needs_target = kind in ("number", "field") or (kind == "yesno" and values.get("period") == "week")
    if needs_target and not values.get("target"):
        raise ValueError("Set a target")
    if kind == "rating" and values.get("period") == "week":
        raise ValueError("A rating is scored day by day")


def set_builtin(db: Session, user: User, code: str, active: bool) -> None:
    if code not in dict(character_stats.STATS):
        raise ValueError("Unknown stat")
    profile = profiles.get_profile(db, user)
    custom = dict(profile.customization or {})
    hidden = [c for c in custom.get("hidden", []) if c != code]
    if not active:
        hidden.append(code)
    custom["hidden"] = hidden
    profile.customization = custom  # a new dict, so the JSON column is saved
    db.commit()
