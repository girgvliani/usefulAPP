from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Todo, User
from app.schemas import TodoIn, TodoOut
from app.services import rpg_logic

router = APIRouter(prefix="/todos", tags=["todos"])


@router.get("", response_model=list[TodoOut])
def list_todos(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return list(
        db.scalars(select(Todo).where(Todo.user_id == current_user.id).order_by(Todo.deadline))
    )


@router.post("", response_model=TodoOut, status_code=status.HTTP_201_CREATED)
def create_todo(payload: TodoIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    todo = rpg_logic.add_todo(db, current_user, payload.task, payload.area_id, payload.base_xp, payload.deadline)
    if not todo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Life area not found")
    return todo


@router.post("/{todo_id}/complete", response_model=TodoOut)
def complete_todo(todo_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    todo = rpg_logic.complete_todo(db, current_user, todo_id)
    if not todo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found or already completed")
    return todo
