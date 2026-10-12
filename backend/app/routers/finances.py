from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Subscription, User
from app.services import finances, profiles

router = APIRouter(prefix="/finances", tags=["finances"])

Cycle = Literal["weekly", "monthly", "quarterly", "yearly"]


class SubscriptionIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    amount: float = Field(ge=0, le=1e7)
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")  # defaults to the profile's
    cycle: Cycle = "monthly"
    next_due: date
    category: str | None = Field(default=None, max_length=40)
    note: str | None = Field(default=None, max_length=200)
    autopay: bool = True  # charged automatically (rolls forward by itself) or paid by hand
    active: bool = True
    remind_days: int = Field(default=2, ge=0, le=30)  # remind this many days before


class SubscriptionUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    amount: float | None = Field(default=None, ge=0, le=1e7)
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    cycle: Cycle | None = None
    next_due: date | None = None
    category: str | None = Field(default=None, max_length=40)
    note: str | None = Field(default=None, max_length=200)
    autopay: bool | None = None
    active: bool | None = None
    remind_days: int | None = Field(default=None, ge=0, le=30)


def _subs(db: Session, user: User) -> list[Subscription]:
    return list(db.scalars(select(Subscription).where(Subscription.user_id == user.id)))


def _get(db: Session, user: User, sub_id: int) -> Subscription:
    sub = db.scalar(select(Subscription).where(Subscription.id == sub_id, Subscription.user_id == user.id))
    if not sub:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such subscription")
    return sub


def _overview(db: Session, user: User) -> dict:
    today = profiles.today(db, user)
    subs = _subs(db, user)
    if any([finances.roll(s, today) for s in subs]):  # automatic payments whose date has passed
        db.commit()
    return finances.overview(subs, today, profiles.get_profile(db, user).currency)


@router.get("")
def get_finances(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Every subscription and recurring bill, soonest first; totals a month and a year per currency;
    what's due in the next 30 days"""
    return _overview(db, current_user)


@router.post("/subscriptions", status_code=status.HTTP_201_CREATED)
def add_subscription(payload: SubscriptionIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    data = payload.model_dump()
    data["currency"] = data["currency"] or profiles.get_profile(db, current_user).currency
    db.add(Subscription(user_id=current_user.id, due_day=payload.next_due.day, **data))
    db.commit()
    return _overview(db, current_user)


@router.patch("/subscriptions/{sub_id}")
def update_subscription(sub_id: int, payload: SubscriptionUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sub = _get(db, current_user, sub_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        if value is None and key not in ("category", "note"):
            continue
        setattr(sub, key, value)
        if key == "next_due":
            sub.due_day = value.day  # a new date sets the day it keeps
    db.commit()
    return _overview(db, current_user)


@router.post("/subscriptions/{sub_id}/paid")
def mark_paid(sub_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Paid this one: the next due date moves one cycle on"""
    sub = _get(db, current_user, sub_id)
    sub.last_paid = sub.next_due
    sub.next_due = finances.after(sub.next_due, sub.cycle, sub.due_day)
    db.commit()
    return _overview(db, current_user)


@router.delete("/subscriptions/{sub_id}")
def delete_subscription(sub_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.delete(_get(db, current_user, sub_id))
    db.commit()
    return _overview(db, current_user)
