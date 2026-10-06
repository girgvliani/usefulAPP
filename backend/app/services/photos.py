"""Profile photos: re-encoded to a 256 px square JPEG (which drops EXIF, so no location or camera data),
stored in the database, and served at /photos/{token}.jpg. Others get the URL only where they'd see
your name: friends and the leaderboard, unless you chose to show just your code."""

import io
import secrets

from PIL import Image, ImageOps
from sqlalchemy.orm import Session

from app.models import ProfilePhoto, User
from app.services import profiles

SIZE = 256
MAX_BYTES = 8 * 1024 * 1024
Image.MAX_IMAGE_PIXELS = 50_000_000  # bigger raises instead of decoding a decompression bomb


def clean(raw: bytes) -> bytes:
    """Any photo → a 256 px centre-cropped JPEG. Raises ValueError if it isn't an image."""
    try:
        with Image.open(io.BytesIO(raw)) as image:
            image = ImageOps.exif_transpose(image).convert("RGB")
            square = ImageOps.fit(image, (SIZE, SIZE), Image.Resampling.LANCZOS)
    except (OSError, Image.DecompressionBombError, ValueError) as err:
        raise ValueError("That isn't a photo we can read (JPEG, PNG or WebP)") from err
    out = io.BytesIO()
    square.save(out, "JPEG", quality=85, optimize=True)
    return out.getvalue()


def save(db: Session, user: User, raw: bytes) -> ProfilePhoto:
    data = clean(raw)
    photo = db.get(ProfilePhoto, user.id) or ProfilePhoto(user_id=user.id)
    photo.data, photo.token = data, secrets.token_urlsafe(18)
    db.add(photo)
    db.commit()
    return photo


def remove(db: Session, user: User) -> None:
    if photo := db.get(ProfilePhoto, user.id):
        db.delete(photo)
        db.commit()


def new_token(db: Session, user: User) -> None:
    """A fresh URL, so links handed out before stop working (on hiding your name)"""
    if photo := db.get(ProfilePhoto, user.id):
        photo.token = secrets.token_urlsafe(18)
        db.commit()


def url(photo: ProfilePhoto | None) -> str | None:
    return f"/photos/{photo.token}.jpg" if photo else None


def own_url(db: Session, user: User) -> str | None:
    return url(db.get(ProfilePhoto, user.id))


def public_url(db: Session, user: User) -> str | None:
    """What others see: the photo goes with your name, so 'just your code' hides it"""
    if profiles.get_profile(db, user).public_name == "code":
        return None
    return own_url(db, user)
