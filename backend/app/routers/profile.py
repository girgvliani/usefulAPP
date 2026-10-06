from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas import ProfileOut, ProfileUpdate
from app.services import achievements, photos, profiles

router = APIRouter(prefix="/profile", tags=["profile"])


def _out(db: Session, user: User) -> ProfileOut:
    profile = profiles.get_profile(db, user)
    return ProfileOut.model_validate(profile).model_copy(update={
        "photo_url": photos.own_url(db, user), "title": achievements.worn_title(db, user),
    })


@router.get("", response_model=ProfileOut)
def get_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Your personal targets, currency and timezone, your photo and the title you wear."""
    return _out(db, current_user)


@router.patch("", response_model=ProfileOut)
def update_profile(payload: ProfileUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = profiles.get_profile(db, current_user)
    hiding = payload.public_name == "code" and profile.public_name != "code"
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(profile, field, value)
    db.commit()
    if hiding:  # links to the photo that friends already have stop working
        photos.new_token(db, current_user)
    return _out(db, current_user)


@router.put("/photo", response_model=ProfileOut)
def upload_photo(photo: UploadFile = File(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """A new profile photo: any JPEG, PNG or WebP up to 8 MB, cropped to a 256 px square"""
    raw = photo.file.read(photos.MAX_BYTES + 1)
    if len(raw) > photos.MAX_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="The photo is over 8 MB")
    try:
        photos.save(db, current_user, raw)
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=str(err))
    return _out(db, current_user)


@router.delete("/photo", response_model=ProfileOut)
def delete_photo(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    photos.remove(db, current_user)
    return _out(db, current_user)
