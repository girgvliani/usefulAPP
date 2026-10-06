from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Friendship, User, UserProfile
from app.services import friends, profiles

router = APIRouter(prefix="/friends", tags=["friends"])


class FriendRequestIn(BaseModel):
    """A friend code (K7QF-M2XA) or an email"""
    code: str | None = Field(default=None, max_length=12)
    email: str | None = Field(default=None, max_length=255)


class SharingIn(BaseModel):
    level: bool | None = None
    stats: bool | None = None
    streaks: bool | None = None
    goals: bool | None = None


def _person(db: Session, user: User) -> dict:
    return {"id": user.id, "name": friends.name_of(db, user), "code": friends.friend_code(db, user)}


@router.get("")
def overview(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Your code and sharing switches, your friends (with only what each shares), and open requests."""
    incoming, outgoing = [], []
    rows = db.scalars(select(Friendship).where(
        Friendship.status == "pending",
        (Friendship.requester_id == current_user.id) | (Friendship.addressee_id == current_user.id),
    ))
    for row in rows:
        mine = row.requester_id == current_user.id
        other = db.get(User, row.addressee_id if mine else row.requester_id)
        (outgoing if mine else incoming).append({"request_id": row.id, **_person(db, other)})
    return {
        "code": friends.friend_code(db, current_user),
        "sharing": friends.sharing(db, current_user),
        "friends": [friends.shared(db, f) for f in friends.friends_of(db, current_user)],
        "incoming": incoming,
        "outgoing": outgoing,
    }


@router.patch("/sharing")
def update_sharing(payload: SharingIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Turn sharing on or off; it applies to all your friends at once."""
    profile = profiles.get_profile(db, current_user)
    for key, value in payload.model_dump(exclude_none=True).items():
        setattr(profile, f"share_{key}", value)
    db.commit()
    return friends.sharing(db, current_user)


@router.post("/requests", status_code=status.HTTP_201_CREATED)
def send_request(payload: FriendRequestIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Ask someone by code or email. If they already asked you, you're friends right away."""
    if payload.code:
        code = payload.code.strip().upper()
        if "-" not in code and len(code) == 8:
            code = f"{code[:4]}-{code[4:]}"
        profile = db.scalar(select(UserProfile).where(UserProfile.friend_code == code))
        other = db.get(User, profile.user_id) if profile else None
        if not other:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No one has that friend code")
    elif payload.email:
        other = db.scalar(select(User).where(func.lower(User.email) == payload.email.strip().lower()))
        if not other:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No account with that email")
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Send a friend code or an email")
    if other.id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="That's you")
    try:
        result = friends.request(db, current_user, other)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    return {"status": result, **_person(db, other)}


def _own_request(db: Session, user: User, request_id: int) -> Friendship:
    row = db.scalar(select(Friendship).where(Friendship.id == request_id, Friendship.status == "pending"))
    if not row or user.id not in (row.requester_id, row.addressee_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    return row


@router.post("/requests/{request_id}/accept")
def accept_request(request_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = _own_request(db, current_user, request_id)
    if row.addressee_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the person you asked can accept")
    friends.accept(db, row)
    return _person(db, db.get(User, row.requester_id))


@router.delete("/requests/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
def drop_request(request_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Decline a request to you, or take back one you sent."""
    db.delete(_own_request(db, current_user, request_id))
    db.commit()


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_friend(user_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Unfriend: they stop seeing anything of yours, and you of theirs."""
    other = db.get(User, user_id)
    row = friends.friendship(db, current_user, other) if other else None
    if not row or row.status != "accepted":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not your friend")
    db.delete(row)
    db.commit()


@router.get("/leaderboard")
def leaderboard(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """You and your friends, each with what they share: level and XP this week, TOTAL and how it moved
    this week, and the six categories. The apps sort it by whichever column you pick."""
    parts = ("level", "stats")
    rows = [{**friends.shared(db, current_user, everything=True, parts=parts), "me": True}]
    rows += [{**friends.shared(db, f, parts=parts), "me": False} for f in friends.friends_of(db, current_user)]
    return rows
