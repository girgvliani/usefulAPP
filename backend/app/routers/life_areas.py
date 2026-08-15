from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import LifeArea, User
from app.schemas import LifeAreaOut

router = APIRouter(prefix="/life-areas", tags=["life-areas"])


@router.get("", response_model=list[LifeAreaOut])
def list_life_areas(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return list(db.scalars(select(LifeArea).where(LifeArea.user_id == current_user.id).order_by(LifeArea.name)))
