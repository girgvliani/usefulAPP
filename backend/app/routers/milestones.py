from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import EpicMilestone, User
from app.schemas import MilestoneOut
from app.services import rpg_logic

router = APIRouter(prefix="/milestones", tags=["milestones"])


@router.get("", response_model=list[MilestoneOut])
def list_milestones(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return list(db.scalars(select(EpicMilestone).where(EpicMilestone.user_id == current_user.id)))


@router.post("/{key}/complete", response_model=MilestoneOut)
def complete_milestone(key: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    milestone = rpg_logic.complete_epic_milestone(db, current_user, key)
    if not milestone:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Milestone not found or already completed")
    return milestone
