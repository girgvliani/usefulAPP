"""Chrome history import: the history itself is read in the browser and never sent; only each day's
totals per category (as the daily-log "browser" section) and the user's site groups reach the server."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import User
from app.services import profiles

router = APIRouter(prefix="/browsing", tags=["browsing"])

CATEGORIES = ("work", "learning", "social", "entertainment", "shopping", "news", "other", "ignore")


class SiteGroupsIn(BaseModel):
    """site (host, with its port: "localhost:3000") -> category"""
    groups: dict[str, str] = Field(max_length=5000)

    @field_validator("groups")
    @classmethod
    def known(cls, groups: dict[str, str]) -> dict[str, str]:
        for site, category in groups.items():
            if not site or len(site) > 200:
                raise ValueError(f"'{site[:40]}' isn't a site")
            if category not in CATEGORIES:
                raise ValueError(f"{site}: category must be one of {', '.join(CATEGORIES)}")
        return groups


@router.get("/groups")
def get_groups(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """The categories you've given sites, and the categories there are"""
    return {"categories": CATEGORIES, "groups": profiles.get_profile(db, current_user).site_groups or {}}


@router.put("/groups")
def save_groups(payload: SiteGroupsIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Merges into what's saved: sites you don't send keep their category"""
    profile = profiles.get_profile(db, current_user)
    profile.site_groups = {**(profile.site_groups or {}), **payload.groups}
    db.commit()
    return {"categories": CATEGORIES, "groups": profile.site_groups}
