from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas import PushupIn, ShowerResult, WorkoutResult
from app.serializers import xp_result_to_schema
from app.services import rpg_logic

router = APIRouter(prefix="/habits", tags=["habits"])


@router.post("/workout", response_model=WorkoutResult)
def log_workout(payload: PushupIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = rpg_logic.track_pushups(db, current_user, payload.count)
    return WorkoutResult(
        met_requirement=result["met_requirement"],
        streak=result["streak"],
        bonus_xp=result["bonus_xp"],
        consistency_bonus=result["consistency_bonus"],
        xp_result=xp_result_to_schema(result["xp_result"]),
    )


@router.post("/shower", response_model=ShowerResult)
def log_shower(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = rpg_logic.check_shower(db, current_user)
    return ShowerResult(
        already_logged=result["already_logged"],
        streak=result["streak"],
        xp_result=xp_result_to_schema(result.get("xp_result")),
    )
