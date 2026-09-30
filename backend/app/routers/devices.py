from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_device, get_session_user
from app.models import DeviceToken, User
from app.schemas import DeviceCreated, DeviceIn, DeviceOut
from app.security import new_device_token

router = APIRouter(prefix="/devices", tags=["devices"])


@router.post("", response_model=DeviceCreated, status_code=status.HTTP_201_CREATED)
def create_device(payload: DeviceIn, current_user: User = Depends(get_session_user), db: Session = Depends(get_db)):
    token, token_hash = new_device_token()
    device = DeviceToken(user_id=current_user.id, name=payload.name, token_hash=token_hash)
    db.add(device)
    db.commit()
    db.refresh(device)
    return DeviceCreated(
        id=device.id, name=device.name, created_at=device.created_at, last_used_at=device.last_used_at, token=token
    )


@router.get("/me", response_model=DeviceOut)
def this_device(device: DeviceToken = Depends(get_current_device)):
    """For a device to check its token works (and see which device it is)."""
    return device


@router.get("", response_model=list[DeviceOut])
def list_devices(current_user: User = Depends(get_session_user), db: Session = Depends(get_db)):
    return list(db.scalars(select(DeviceToken).where(DeviceToken.user_id == current_user.id).order_by(DeviceToken.id)))


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_device(device_id: int, current_user: User = Depends(get_session_user), db: Session = Depends(get_db)):
    device = db.scalar(select(DeviceToken).where(DeviceToken.user_id == current_user.id, DeviceToken.id == device_id))
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    db.delete(device)
    db.commit()
