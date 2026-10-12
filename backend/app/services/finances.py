"""Manage finances: subscriptions and recurring bills, what each costs and when it's next due.

Each one bills every week, month, quarter or year. Automatic ones (cards charged by the service) roll
forward on their own once the date passes; manual ones (bills you pay yourself) stay "overdue" until
marked paid. Monthly dates keep their day: something due on the 31st is due on the 28th/29th in
February and back on the 31st in March. Totals are per currency (no exchange rates are guessed).
"""

import calendar
from collections import defaultdict
from datetime import date, timedelta

from app.models import Subscription

CYCLES = {"weekly": "Weekly", "monthly": "Monthly", "quarterly": "Every 3 months", "yearly": "Yearly"}
# How many of each cycle fit in a month / a year, for the totals
PER_MONTH = {"weekly": 52 / 12, "monthly": 1, "quarterly": 1 / 3, "yearly": 1 / 12}
CATEGORIES = ["Streaming", "Music", "Software", "Cloud & storage", "Phone & internet", "Gym & health",
              "News & reading", "Gaming", "Insurance", "Rent & utilities", "Loans", "Other"]
SOON_DAYS = 7


def _add_months(day: date, months: int, anchor: int) -> date:
    month = day.month - 1 + months
    year, month = day.year + month // 12, month % 12 + 1
    return date(year, month, min(anchor, calendar.monthrange(year, month)[1]))


def after(due: date, cycle: str, anchor: int) -> date:
    """The due date one cycle after `due`"""
    if cycle == "weekly":
        return due + timedelta(days=7)
    return _add_months(due, {"monthly": 1, "quarterly": 3, "yearly": 12}[cycle], anchor)


def roll(sub: Subscription, today: date) -> bool:
    """Automatic payments: move a passed due date forward to the next one. True if it moved."""
    moved = False
    while sub.autopay and sub.next_due < today:
        sub.last_paid = sub.next_due
        sub.next_due = after(sub.next_due, sub.cycle, sub.due_day)
        moved = True
    return moved


def view(sub: Subscription, today: date) -> dict:
    days = (sub.next_due - today).days
    status = ("paused" if not sub.active else "overdue" if days < 0 else "today" if days == 0
              else "soon" if days <= SOON_DAYS else "later")
    return {
        "id": sub.id, "name": sub.name, "amount": sub.amount, "currency": sub.currency, "cycle": sub.cycle,
        "cycle_label": CYCLES[sub.cycle], "next_due": sub.next_due.isoformat(), "days_until": days, "status": status,
        "category": sub.category, "note": sub.note, "autopay": sub.autopay, "active": sub.active,
        "remind_days": sub.remind_days, "last_paid": sub.last_paid.isoformat() if sub.last_paid else None,
        "monthly": round(sub.amount * PER_MONTH[sub.cycle], 2),
        "yearly": round(sub.amount * PER_MONTH[sub.cycle] * 12, 2),
    }


def charges_between(sub: Subscription, start: date, end: date) -> list[date]:
    """Every due date of an active subscription from start to end (inclusive)"""
    if not sub.active:
        return []
    out, due = [], sub.next_due
    while due <= end:
        if due >= start:
            out.append(due)
        due = after(due, sub.cycle, sub.due_day)
    return out


def overview(subs: list[Subscription], today: date, currency: str) -> dict:
    """Every subscription, soonest first, with totals per currency and what's due in the next 30 days"""
    views = sorted((view(s, today) for s in subs), key=lambda v: (not v["active"], v["next_due"], v["name"].lower()))
    monthly, yearly, next_30 = defaultdict(float), defaultdict(float), defaultdict(float)
    by_category: dict[str, dict] = defaultdict(lambda: defaultdict(float))
    upcoming = []
    horizon = today + timedelta(days=30)
    for sub in subs:
        if not sub.active:
            continue
        per_month = sub.amount * PER_MONTH[sub.cycle]
        monthly[sub.currency] += per_month
        yearly[sub.currency] += per_month * 12
        by_category[sub.category or "Other"][sub.currency] += per_month
        for due in charges_between(sub, today if sub.autopay else min(today, sub.next_due), horizon):
            next_30[sub.currency] += sub.amount
            upcoming.append({"id": sub.id, "name": sub.name, "amount": sub.amount, "currency": sub.currency,
                             "date": due.isoformat(), "days_until": (due - today).days})
    upcoming.sort(key=lambda u: (u["date"], u["name"].lower()))
    rounded = lambda d: {k: round(v, 2) for k, v in sorted(d.items(), key=lambda kv: (kv[0] != currency, kv[0]))}
    return {
        "currency": currency,
        "subscriptions": views,
        "upcoming": upcoming,
        "totals": {
            "active": sum(1 for s in subs if s.active),
            "monthly": rounded(monthly), "yearly": rounded(yearly), "next_30_days": rounded(next_30),
            "by_category": sorted(
                ({"category": c, "monthly": rounded(v)} for c, v in by_category.items()),
                key=lambda row: -sum(row["monthly"].values()),
            ),
        },
        "cycles": CYCLES,
        "categories": CATEGORIES,
    }
