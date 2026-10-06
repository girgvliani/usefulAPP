from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import User
from app.services import achievements

router = APIRouter(prefix="/achievements", tags=["achievements"])


class TitleIn(BaseModel):
    key: str | None = Field(default=None, max_length=40)  # null: back to the level title


@router.get("")
def list_achievements(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Every achievement (how to get it, its XP and title, your progress), the stories they belong to,
    and the title you wear. Checks for newly reached ones first."""
    achievements.evaluate(db, current_user)
    return achievements.overview(db, current_user)


@router.get("/catalog")
def catalog():
    """The stories and achievements, without anyone's progress"""
    return {
        "stories": [vars(s) for s in achievements.STORIES],
        "achievements": [{**achievements.brief(a), "how": a.how, "target": a.target, "unit": a.unit} for a in achievements.ACHIEVEMENTS],
    }


@router.post("/seen", status_code=status.HTTP_204_NO_CONTENT)
def seen(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """The unlock screen was shown: stop listing these in /stats/level new_achievements"""
    achievements.mark_seen(db, current_user)


@router.put("/title")
def wear_title(payload: TitleIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Wear an earned achievement's title (friends and the leaderboard see it instead of the level title)"""
    try:
        achievements.wear(db, current_user, payload.key)
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))
    return {"title": payload.key, "name": achievements.TITLES.get(payload.key) if payload.key else None}
