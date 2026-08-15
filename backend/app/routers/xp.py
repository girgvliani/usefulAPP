from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas import LifeAreaOut, ManualXpIn
from app.services import rpg_logic

router = APIRouter(prefix="/xp", tags=["xp"])


@router.post("/manual", response_model=LifeAreaOut)
def manual_xp_adjustment(payload: ManualXpIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    area = rpg_logic.manual_xp_adjustment(db, current_user, payload.area_id, payload.xp)
    if not area:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Life area not found")
    return area
