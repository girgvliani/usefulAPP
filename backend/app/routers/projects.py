from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Income, Project, User
from app.schemas import ProjectIn, ProjectOut, ProjectUpdate
from app.services import rpg_logic

router = APIRouter(prefix="/projects", tags=["projects"])


def _owned_project(db: Session, user: User, project_id: int) -> Project:
    project = db.scalar(select(Project).where(Project.user_id == user.id, Project.id == project_id))
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


@router.get("", response_model=list[ProjectOut])
def list_projects(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return list(
        db.scalars(select(Project).where(Project.user_id == current_user.id).order_by(Project.created_at.desc()))
    )


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return rpg_logic.add_project(db, current_user, payload.name, payload.value, payload.deadline)


@router.post("/{project_id}/complete", response_model=ProjectOut)
def complete_project(project_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = rpg_logic.complete_project(db, current_user, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found or already completed")
    return project


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _owned_project(db, current_user, project_id)


@router.patch("/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: int, payload: ProjectUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    project = _owned_project(db, current_user, project_id)
    changes = payload.model_dump(exclude_none=True)
    if project.completed and "value" in changes:
        # Keep this month's earnings in step with the corrected value
        income = db.scalar(select(Income).where(Income.user_id == current_user.id))
        income.current_month_earnings = max(0, income.current_month_earnings + changes["value"] - project.value)
    for key, value in changes.items():
        setattr(project, key, value)
    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """A completed project's value comes off this month's earnings; XP already earned stays."""
    project = _owned_project(db, current_user, project_id)
    if project.completed:
        income = db.scalar(select(Income).where(Income.user_id == current_user.id))
        income.current_month_earnings = max(0, income.current_month_earnings - project.value)
    db.delete(project)
    db.commit()
