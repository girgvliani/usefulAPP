import re

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import EpicMilestone, User
from app.schemas import MilestoneIn, MilestoneOut, MilestoneUpdate
from app.services import rpg_logic

router = APIRouter(prefix="/milestones", tags=["milestones"])


def _owned_milestone(db: Session, user: User, key: str) -> EpicMilestone:
    milestone = db.scalar(select(EpicMilestone).where(EpicMilestone.user_id == user.id, EpicMilestone.key == key))
    if not milestone:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Milestone not found")
    return milestone


def _new_key(db: Session, user: User, description: str) -> str:
    """URL-safe key from the description ("Run a marathon" -> run_a_marathon), unique per user."""
    base = re.sub(r"[^a-z0-9]+", "_", description.lower()).strip("_")[:80] or "milestone"
    taken = set(db.scalars(select(EpicMilestone.key).where(EpicMilestone.user_id == user.id)))
    key, n = base, 2
    while key in taken:
        key, n = f"{base}_{n}", n + 1
    return key


@router.get("", response_model=list[MilestoneOut])
def list_milestones(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return list(db.scalars(select(EpicMilestone).where(EpicMilestone.user_id == current_user.id)))


@router.post("", response_model=MilestoneOut, status_code=status.HTTP_201_CREATED)
def create_milestone(payload: MilestoneIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    milestone = EpicMilestone(
        user_id=current_user.id,
        key=_new_key(db, current_user, payload.description),
        description=payload.description,
        xp_reward=payload.xp_reward,
        completed=False,
    )
    db.add(milestone)
    db.commit()
    db.refresh(milestone)
    return milestone


@router.patch("/{key}", response_model=MilestoneOut)
def update_milestone(
    key: str, payload: MilestoneUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    milestone = _owned_milestone(db, current_user, key)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(milestone, field, value)
    db.commit()
    db.refresh(milestone)
    return milestone


@router.delete("/{key}", status_code=status.HTTP_204_NO_CONTENT)
def delete_milestone(key: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.delete(_owned_milestone(db, current_user, key))
    db.commit()


@router.post("/{key}/complete", response_model=MilestoneOut)
def complete_milestone(key: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    milestone = rpg_logic.complete_epic_milestone(db, current_user, key)
    if not milestone:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Milestone not found or already completed")
    return milestone
