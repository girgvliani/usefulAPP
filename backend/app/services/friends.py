"""Friends: codes, requests, and what each person chooses to share.

Nothing is shared until its switch is on, and the switches apply to all friends alike:
- level: LV, title, XP, and XP earned this week
- stats: TOTAL, the six categories and nine stats (scores and ranks), and how TOTAL moved this week
- streaks: current and best streaks
- goals: goal titles and progress (never the numbers behind them, like a weight)
A friend sees your display name (or your code), never your email.
"""

import secrets
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import Friendship, Goal, GoalType, User, UserProfile
from app.services import character_stats, daily_logs, goals, levels, profiles, streaks

CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O or 1/I to misread
SHARES = ("level", "stats", "streaks", "goals")


def friend_code(db: Session, user: User) -> str:
    """The user's code, made on first use: e.g. K7QF-M2XA"""
    profile = profiles.get_profile(db, user)
    while not profile.friend_code:
        code = "-".join("".join(secrets.choice(CODE_ALPHABET) for _ in range(4)) for _ in range(2))
        if not db.scalar(select(UserProfile).where(UserProfile.friend_code == code)):
            profile.friend_code = code
            db.commit()
    return profile.friend_code


def name_of(db: Session, user: User) -> str:
    """What others see, as the user chose: their name, their nickname, or just their friend code"""
    profile = profiles.get_profile(db, user)
    chosen = {"name": profile.display_name, "nickname": profile.nickname}.get(profile.public_name)
    return chosen or f"Player {friend_code(db, user)}"


def sharing(db: Session, user: User) -> dict:
    """The four friend switches, plus whether you're on the global leaderboard"""
    profile = profiles.get_profile(db, user)
    return {**{key: getattr(profile, f"share_{key}") for key in SHARES}, "leaderboard": profile.on_leaderboard}


GLOBAL_TOP = 50


def global_board(db: Session, me: User) -> dict:
    """Everyone on the global leaderboard by XP: name, level, title, XP. The top 50, plus your own place
    when you're further down (or hidden: then only you see your row, unranked)."""
    users = list(db.scalars(select(User).join(UserProfile, UserProfile.user_id == User.id).where(UserProfile.on_leaderboard)))
    rows = []
    for user in users:
        summary = levels.summary(db, user)
        rows.append({"id": user.id, "name": name_of(db, user), "level": summary["level"], "title": summary["title"],
                     "xp": summary["xp"], "me": user.id == me.id})
    rows.sort(key=lambda r: (-r["xp"], r["name"]))
    for i, row in enumerate(rows):
        row["rank"] = i + 1
    mine = next((r for r in rows if r["me"]), None)
    if mine is None:  # hidden: show you where you'd be, without a rank
        summary = levels.summary(db, me)
        mine = {"id": me.id, "name": name_of(db, me), "level": summary["level"], "title": summary["title"],
                "xp": summary["xp"], "me": True, "rank": None}
    return {"players": len(rows), "top": rows[:GLOBAL_TOP], "you": mine}


def friendship(db: Session, a: User, b: User) -> Friendship | None:
    """The row between two people, whoever asked"""
    return db.scalar(select(Friendship).where(or_(
        (Friendship.requester_id == a.id) & (Friendship.addressee_id == b.id),
        (Friendship.requester_id == b.id) & (Friendship.addressee_id == a.id),
    )))


def friends_of(db: Session, user: User) -> list[User]:
    rows = db.scalars(select(Friendship).where(
        Friendship.status == "accepted", or_(Friendship.requester_id == user.id, Friendship.addressee_id == user.id),
    ))
    ids = [r.addressee_id if r.requester_id == user.id else r.requester_id for r in rows]
    return list(db.scalars(select(User).where(User.id.in_(ids)))) if ids else []


def request(db: Session, me: User, other: User) -> str:
    """Sends a request; if they already asked me, that's a yes. Returns "pending" or "accepted"."""
    existing = friendship(db, me, other)
    if existing and existing.status == "accepted":
        raise ValueError("You're already friends")
    if existing and existing.requester_id == me.id:
        raise ValueError("You've already sent a request; it's waiting for them")
    if existing:  # they asked first
        accept(db, existing)
        return "accepted"
    db.add(Friendship(requester_id=me.id, addressee_id=other.id, status="pending"))
    db.commit()
    return "pending"


def accept(db: Session, row: Friendship) -> None:
    row.status = "accepted"
    row.accepted_at = datetime.now(timezone.utc)
    db.commit()


def _sheet(db: Session, user: User, day: date) -> dict:
    profile = profiles.get_profile(db, user)
    data = daily_logs.stats_input(db, user, day)
    return character_stats.character_sheet(data, day.isoformat(), profile.pushup_target, profile.sleep_target)


def _grade(score):
    return character_stats.grade(score) if score is not None else None


def shared(db: Session, user: User, everything: bool = False, parts: tuple = SHARES) -> dict:
    """What a friend may see of `user`: only what their switches allow (everything: your own row).
    parts: which of them to work out at all."""
    allowed = {key: True for key in SHARES} if everything else sharing(db, user)
    on = {key: allowed[key] and key in parts for key in SHARES}
    view = {"id": user.id, "name": name_of(db, user), "code": friend_code(db, user), "shares": allowed}
    today = profiles.today(db, user)

    if on["level"]:
        summary = levels.summary(db, user)
        view["level"] = {
            "level": summary["level"], "title": summary["title"], "xp": summary["xp"],
            # Activity XP of the last 7 days (quest XP has no dates)
            "week_xp": sum(day["xp"] for day in summary["history"][-7:]),
        }
    if on["stats"]:
        now, week_ago = _sheet(db, user, today), _sheet(db, user, today - timedelta(days=7))
        view["stats"] = {
            "total": now["overall"], "total_grade": _grade(now["overall"]),
            "total_change": None if now["overall"] is None or week_ago["overall"] is None else now["overall"] - week_ago["overall"],
            "categories": [
                {"key": key, "name": name, "score": now["categories"][key], "grade": _grade(now["categories"][key]),
                 "change": None if now["categories"][key] is None or week_ago["categories"][key] is None
                 else now["categories"][key] - week_ago["categories"][key]}
                for key, name, _ in character_stats.CATEGORIES
            ],
            "stats": [
                {"code": code, "name": name, "score": now["stats"][code]["score"], "grade": _grade(now["stats"][code]["score"])}
                for code, name in character_stats.STATS
            ],
        }
    if on["streaks"]:
        view["streaks"] = [
            {"key": s["key"], "name": s["name"], "emoji": s["emoji"], "current": s["current"], "best": s["best"]}
            for s in streaks.streaks(db, user)["streaks"]
        ]
    if on["goals"]:
        data = daily_logs.stats_input(db, user, today)
        rows = db.scalars(select(Goal).where(Goal.user_id == user.id).order_by(Goal.created_at))
        view["goals"] = []
        for goal in rows:
            progress = goals.progress(goal.start_value, goal.target_value, goals.current_value(goal, data, today.isoformat()))
            view["goals"].append({"title": public_title(goal), "progress": progress, "achieved": progress == 1, "deadline": goal.deadline})
    return view


def public_title(goal: Goal) -> str:
    """A goal's name without its numbers ("Weight: 112 → 107 kg" → "Lose weight"); your own wording for custom goals"""
    if goal.type == GoalType.custom:
        return goal.title
    if goal.type == GoalType.weight:
        return "Lose weight" if goal.target_value < goal.start_value else "Gain weight"
    return goals.LABELS[goal.type]

