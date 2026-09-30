from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import LifeArea, Todo, User
from app.schemas import LifeAreaIn, LifeAreaOut
from app.services import rpg_logic

router = APIRouter(prefix="/life-areas", tags=["life-areas"])


def _owned_area(db: Session, user: User, area_id: int) -> LifeArea:
    area = rpg_logic.get_life_area(db, user, area_id)
    if not area:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Life area not found")
    return area


def _check_name_free(db: Session, user: User, name: str) -> None:
    if db.scalar(select(LifeArea).where(LifeArea.user_id == user.id, LifeArea.name == name)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You already have an area with that name")


def _check_not_protected(area: LifeArea) -> None:
    if area.name in rpg_logic.PROTECTED_AREAS:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"'{area.name}' is used by habit XP and can't change")


@router.get("", response_model=list[LifeAreaOut])
def list_life_areas(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return list(db.scalars(select(LifeArea).where(LifeArea.user_id == current_user.id).order_by(LifeArea.name)))


@router.post("", response_model=LifeAreaOut, status_code=status.HTTP_201_CREATED)
def create_life_area(payload: LifeAreaIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Name it "Category - Skill" (e.g. "Work Skills - Kotlin") to group it with others."""
    _check_name_free(db, current_user, payload.name)
    area = LifeArea(user_id=current_user.id, name=payload.name, level=1, xp=0)
    db.add(area)
    db.commit()
    db.refresh(area)
    return area


@router.get("/{area_id}", response_model=LifeAreaOut)
def get_life_area(area_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _owned_area(db, current_user, area_id)


@router.patch("/{area_id}", response_model=LifeAreaOut)
def rename_life_area(
    area_id: int, payload: LifeAreaIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    area = _owned_area(db, current_user, area_id)
    _check_not_protected(area)
    if payload.name != area.name:
        _check_name_free(db, current_user, payload.name)
    area.name = payload.name
    db.commit()
    db.refresh(area)
    return area


@router.delete("/{area_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_life_area(area_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Refused while todos use the area, so deleting it never silently deletes them."""
    area = _owned_area(db, current_user, area_id)
    _check_not_protected(area)
    todos = db.scalar(select(func.count()).select_from(Todo).where(Todo.area_id == area.id))
    if todos:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=f"{todos} todo(s) use this area; move or delete them first"
        )
    db.delete(area)
    db.commit()
