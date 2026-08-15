from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Income, User
from app.schemas import IncomeOut, IncomeUpdate

router = APIRouter(prefix="/income", tags=["income"])


@router.get("", response_model=IncomeOut)
def get_income(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.scalar(select(Income).where(Income.user_id == current_user.id))


@router.put("", response_model=IncomeOut)
def update_income(payload: IncomeUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    income = db.scalar(select(Income).where(Income.user_id == current_user.id))
    if payload.current_month_earnings is not None:
        income.current_month_earnings = payload.current_month_earnings
    if payload.monthly_goal is not None:
        income.monthly_goal = payload.monthly_goal
    if payload.target_month is not None:
        income.target_month = payload.target_month
    db.commit()
    db.refresh(income)
    return income
