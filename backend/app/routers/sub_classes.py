from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import SubClass, User
from app.services import sub_classes

router = APIRouter(prefix="/sub-classes", tags=["sub-classes"])

ClassKey = Literal["mental", "physical", "practical", "cultural", "discipline", "social"]
Kind = Literal["number", "yesno", "rating", "field"]


class SubClassIn(BaseModel):
    class_key: ClassKey
    name: str = Field(min_length=1, max_length=40)
    icon: str | None = Field(default=None, max_length=8)
    kind: Kind
    field: str | None = Field(default=None, max_length=40)
    unit: str | None = Field(default=None, max_length=16)
    target: float | None = Field(default=None, gt=0, le=1_000_000)
    period: Literal["day", "week"] = "day"
    better: Literal["more", "less"] = "more"


class SubClassPatch(BaseModel):
    class_key: ClassKey | None = None
    name: str | None = Field(default=None, min_length=1, max_length=40)
    icon: str | None = Field(default=None, max_length=8)
    kind: Kind | None = None
    field: str | None = Field(default=None, max_length=40)
    unit: str | None = Field(default=None, max_length=16)
    target: float | None = Field(default=None, gt=0, le=1_000_000)
    period: Literal["day", "week"] | None = None
    better: Literal["more", "less"] | None = None
    active: bool | None = None


class ActiveIn(BaseModel):
    active: bool


def _own(db: Session, user: User, sub_id: int) -> SubClass:
    sub = db.scalar(select(SubClass).where(SubClass.id == sub_id, SubClass.user_id == user.id))
    if sub is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sub-class not found")
    return sub


@router.get("")
def list_sub_classes(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """The six classes with every sub-class (the built-in stats and your own), and the day-log values a
    sub-class can read"""
    return sub_classes.view(db, current_user)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_sub_class(payload: SubClassIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Your own sub-class in one of the six classes"""
    if len(sub_classes.custom_subs(db, current_user)) >= sub_classes.MAX_CUSTOM:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Up to {sub_classes.MAX_CUSTOM} sub-classes")
    values = payload.model_dump()
    if values["kind"] != "field":
        values["field"] = None
    try:
        sub_classes.check(values)
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))
    sub = SubClass(user_id=current_user.id, position=len(sub_classes.custom_subs(db, current_user)), **values)
    db.add(sub)
    db.commit()
    return sub_classes.describe(sub)


@router.patch("/{sub_id}")
def update_sub_class(sub_id: int, payload: SubClassPatch, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sub = _own(db, current_user, sub_id)
    changes = payload.model_dump(exclude_unset=True)
    values = {**sub_classes.describe(sub), **changes}
    if values["kind"] != "field":
        values["field"] = None
    try:
        sub_classes.check(values)
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))
    for key in ("class_key", "name", "icon", "kind", "field", "unit", "target", "period", "better", "active"):
        setattr(sub, key, values[key])
    db.commit()
    return sub_classes.describe(sub)


@router.delete("/{sub_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_sub_class(sub_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Deletes the sub-class; answers already given stay in the day logs, unused"""
    sub = _own(db, current_user, sub_id)
    if sub.path_key:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="It belongs to a path: switch it off, or leave the path")
    db.delete(sub)
    db.commit()


@router.put("/builtin/{code}")
def show_builtin(code: str, payload: ActiveIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Hide a standard stat from its class (it no longer counts in your class or TOTAL), or bring it back"""
    try:
        sub_classes.set_builtin(db, current_user, code, payload.active)
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))
    return sub_classes.view(db, current_user)
