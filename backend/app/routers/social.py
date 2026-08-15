from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas import SocialResult
from app.serializers import xp_result_to_schema
from app.services import rpg_logic

router = APIRouter(prefix="/social-interaction", tags=["social"])


@router.post("", response_model=SocialResult)
def log_social_interaction(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = rpg_logic.log_social_interaction(db, current_user)
    return SocialResult(
        over_limit=result["over_limit"],
        count=result["count"],
        penalty=result.get("penalty"),
        xp_result=xp_result_to_schema(result.get("xp_result")),
    )
