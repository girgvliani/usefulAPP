from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Project, User
from app.schemas import ProjectIn, ProjectOut
from app.services import rpg_logic

router = APIRouter(prefix="/projects", tags=["projects"])


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
