from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ProfilePhoto

router = APIRouter(tags=["photos"])


@router.get("/photos/{token}.jpg")
def get_photo(token: str, db: Session = Depends(get_db)):
    """A profile photo by its token (no sign-in, so <img> tags work; the token changes on every upload)"""
    photo = db.scalar(select(ProfilePhoto).where(ProfilePhoto.token == token))
    if not photo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such photo")
    return Response(photo.data, media_type="image/jpeg", headers={"Cache-Control": "public, max-age=31536000, immutable"})
