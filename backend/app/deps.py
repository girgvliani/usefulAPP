from datetime import datetime, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import DeviceToken, User
from app.security import DEVICE_TOKEN_PREFIX, decode_token, hash_device_token
from app.services import rpg_logic

bearer_scheme = HTTPBearer(auto_error=False)

CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def _user_from_access_token(token: str, db: Session) -> User | None:
    user_id = decode_token(token, expected_type="access")
    return db.get(User, user_id) if user_id is not None else None


def _device_from_token(token: str, db: Session) -> DeviceToken | None:
    device = db.scalar(select(DeviceToken).where(DeviceToken.token_hash == hash_device_token(token)))
    if device is not None:
        device.last_used_at = datetime.now(timezone.utc)
        db.commit()
    return device


def _user_from_device_token(token: str, db: Session) -> User | None:
    device = _device_from_token(token, db)
    return db.get(User, device.user_id) if device else None


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Accepts a login access token or a device token."""
    if credentials is None:
        raise CREDENTIALS_ERROR

    token = credentials.credentials
    if token.startswith(DEVICE_TOKEN_PREFIX):
        user = _user_from_device_token(token, db)
    else:
        user = _user_from_access_token(token, db)
    if user is None:
        raise CREDENTIALS_ERROR

    rpg_logic.apply_daily_decay(db, user)
    return user


def get_session_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Login access tokens only, so a leaked device token can't create or revoke devices."""
    if credentials is None:
        raise CREDENTIALS_ERROR
    user = _user_from_access_token(credentials.credentials, db)
    if user is None:
        raise CREDENTIALS_ERROR
    return user


def get_current_device(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> DeviceToken:
    """Device tokens only: lets a device check its own token."""
    if credentials is None or not credentials.credentials.startswith(DEVICE_TOKEN_PREFIX):
        raise CREDENTIALS_ERROR
    device = _device_from_token(credentials.credentials, db)
    if device is None:
        raise CREDENTIALS_ERROR
    return device
