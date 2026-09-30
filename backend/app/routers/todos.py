from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Todo, User
from app.schemas import TodoIn, TodoOut, TodoUpdate
from app.services import rpg_logic

router = APIRouter(prefix="/todos", tags=["todos"])


def _owned_todo(db: Session, user: User, todo_id: int) -> Todo:
    todo = db.scalar(select(Todo).where(Todo.user_id == user.id, Todo.id == todo_id))
    if not todo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found")
    return todo


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


@router.get("/{todo_id}", response_model=TodoOut)
def get_todo(todo_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _owned_todo(db, current_user, todo_id)


@router.patch("/{todo_id}", response_model=TodoOut)
def update_todo(
    todo_id: int, payload: TodoUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    todo = _owned_todo(db, current_user, todo_id)
    changes = payload.model_dump(exclude_none=True)
    if "area_id" in changes and not rpg_logic.get_life_area(db, current_user, changes["area_id"]):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Life area not found")
    for key, value in changes.items():
        setattr(todo, key, value)
    db.commit()
    db.refresh(todo)
    return todo


@router.delete("/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_todo(todo_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """XP already earned from a completed todo stays."""
    db.delete(_owned_todo(db, current_user, todo_id))
    db.commit()
