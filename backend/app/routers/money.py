from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Literal

from app.database import get_db
from app.deps import get_current_user
from app.models import User
from app.services import baby_steps, profiles

router = APIRouter(prefix="/money", tags=["money"])


class Debt(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    balance: float = Field(ge=0, le=1e9)
    original: float = Field(gt=0, le=1e9)  # what it started at, for progress


class BabyStepsIn(BaseModel):
    """Any of the numbers; ones left out keep their saved value"""
    starter_target: float | None = Field(default=None, gt=0, le=1e7)
    saved: float | None = Field(default=None, ge=0, le=1e9)
    monthly_expenses: float | None = Field(default=None, gt=0, le=1e8)
    months: int | None = Field(default=None, ge=3, le=6)
    debts: list[Debt] | None = Field(default=None, max_length=50)
    invest_percent: float | None = Field(default=None, ge=0, le=100)
    kids: bool | None = None
    college_saved: float | None = Field(default=None, ge=0, le=1e9)
    college_target: float | None = Field(default=None, gt=0, le=1e9)
    home: Literal["renting", "mortgage", "owned"] | None = None
    mortgage_balance: float | None = Field(default=None, ge=0, le=1e10)
    mortgage_original: float | None = Field(default=None, gt=0, le=1e10)
    giving: bool | None = None


def _view(db: Session, user: User) -> dict:
    profile = profiles.get_profile(db, user)
    return {"currency": profile.currency, **baby_steps.steps(profile.baby_steps)}


@router.get("/baby-steps")
def get_baby_steps(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Dave Ramsey's 7 Baby Steps: your numbers, each step's progress, the step you're on"""
    return _view(db, current_user)


@router.put("/baby-steps")
def save_baby_steps(payload: BabyStepsIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = profiles.get_profile(db, current_user)
    changes = payload.model_dump(exclude_none=True)
    profile.baby_steps = {**(profile.baby_steps or {}), **changes}  # a new dict, so the JSON column is saved
    db.commit()
    return _view(db, current_user)
