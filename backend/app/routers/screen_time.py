from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas import ScreenTimeIn, ScreenTimeResult
from app.services import rpg_logic

router = APIRouter(prefix="/screen-time", tags=["screen-time"])


@router.post("", response_model=ScreenTimeResult)
def log_screen_time(payload: ScreenTimeIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = rpg_logic.track_screen_time(db, current_user, payload.hours)
    return ScreenTimeResult(**result)
