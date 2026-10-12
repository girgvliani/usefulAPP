from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import User
from app.routers.paths import _logs
from app.services import books

router = APIRouter(prefix="/books", tags=["books"])


class EntryIn(BaseModel):
    kind: str = Field(max_length=20)
    day: date | None = None
    data: dict[str, Any]


class EntryEdit(BaseModel):
    data: dict[str, Any]


class ReviewIn(BaseModel):
    remembered: bool


class GiftIn(BaseModel):
    friend_id: int


def _run(fn):
    """Service errors → HTTP: no such thing 404, not yours yet 403, not allowed 400"""
    try:
        return fn()
    except LookupError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
    except PermissionError as err:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(err))
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))


@router.get("")
def list_books(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Every book: yours (with chapters read and days practised) and the locked ones with what unlocks
    them. Unlocks any a path level now reaches first ("new")."""
    new = books.sync_unlocks(db, current_user, _logs(db, current_user))
    return books.view(db, current_user, new)


@router.get("/{key}")
def get_book(key: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """One book: its chapters (the text once it's yours) and everything its tracker has logged"""
    books.sync_unlocks(db, current_user, _logs(db, current_user))
    return _run(lambda: books.detail(db, current_user, key))


@router.post("/{key}/chapters/{index}/read")
def read_chapter(key: str, index: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _run(lambda: books.read_chapter(db, current_user, key, index))
    return books.detail(db, current_user, key)


@router.post("/{key}/entries", status_code=status.HTTP_201_CREATED)
def add_entry(key: str, payload: EntryIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Log something in the book's tracker; it also counts towards the matching path sub-class that day"""
    _run(lambda: books.add_entry(db, current_user, key, payload.kind, payload.day, payload.data))
    return books.detail(db, current_user, key)


@router.patch("/{key}/entries/{entry_id}")
def edit_entry(key: str, entry_id: int, payload: EntryEdit, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Change a palace, card or person, or review a decision (review30 / review90)"""
    _run(lambda: books.edit_entry(db, current_user, key, entry_id, payload.data))
    return books.detail(db, current_user, key)


@router.delete("/{key}/entries/{entry_id}")
def delete_entry(key: str, entry_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _run(lambda: books.delete_entry(db, current_user, key, entry_id))
    return books.detail(db, current_user, key)


@router.post("/{key}/entries/{entry_id}/review")
def review_card(key: str, entry_id: int, payload: ReviewIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Spaced repetition: you remembered the card (up a box) or not (back to box 1)"""
    _run(lambda: books.review_card(db, current_user, key, entry_id, payload.remembered))
    return books.detail(db, current_user, key)


@router.post("/{key}/gift")
def gift_book(key: str, payload: GiftIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Give a friend a book you have: one gift a week"""
    message = _run(lambda: books.gift(db, current_user, key, payload.friend_id))
    return {"message": message, **books.view(db, current_user)}
