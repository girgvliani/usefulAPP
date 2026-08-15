from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas import SleepIn, XpResult
from app.serializers import xp_result_to_schema
from app.services import rpg_logic

router = APIRouter(prefix="/sleep", tags=["sleep"])


@router.post("", response_model=XpResult)
def log_sleep(payload: SleepIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = rpg_logic.log_sleep(db, current_user, payload.hours)
    return xp_result_to_schema(result)
