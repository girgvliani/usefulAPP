from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import DailyLog, User
from app.schemas import DailyLogBatchIn, DailyLogIn, DailyLogOut
from app.services import daily_logs, log_fields, profiles

router = APIRouter(prefix="/daily-logs", tags=["daily-logs"])

MAX_RANGE_DAYS = 400
Source = Literal["auto", "manual"]


def _check_not_future(db: Session, user: User, day: date) -> None:
    if day > profiles.today(db, user):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Can't log a future day ({day})")


def _updates(payload: DailyLogIn) -> dict:
    """Only the fields that were sent; None never overwrites, empty sections are dropped."""
    sections = payload.model_dump(exclude_none=True, exclude={"date"})  # batch items carry their date
    return {section: fields for section, fields in sections.items() if fields}


def _to_schema(log: DailyLog) -> DailyLogOut:
    return DailyLogOut(
        date=log.date, auto=log.auto or {}, manual=log.manual or {}, merged=daily_logs.merged(log), updated_at=log.updated_at
    )


@router.get("", response_model=list[DailyLogOut])
def list_logs(start: date, end: date, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if end < start or (end - start).days > MAX_RANGE_DAYS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Range must be 0-{MAX_RANGE_DAYS} days")
    return [_to_schema(log) for log in daily_logs.list_logs(db, current_user, start, end)]


@router.get("/fields")
def list_fields():
    """Every value a day can hold: label, unit, kind, usual source and the stats that read it."""
    return log_fields.catalog()


@router.get("/{day}", response_model=DailyLogOut)
def get_log(day: date, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    log = daily_logs.get_log(db, current_user, day)
    if not log:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nothing logged for that day")
    return _to_schema(log)


@router.put("/{day}", response_model=DailyLogOut)
def save_log(
    day: date,
    payload: DailyLogIn,
    source: Source = "manual",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Merge fields into a day. Devices send source=auto; check-ins use manual, which wins per field."""
    _check_not_future(db, current_user, day)
    return _to_schema(daily_logs.save(db, current_user, day, source, _updates(payload)))


class RepsIn(BaseModel):
    exercise: Literal["pushups", "squats", "situps"]
    count: int = Field(ge=1, le=1000)


@router.post("/{day}/reps", response_model=DailyLogOut)
def add_reps(day: date, payload: RepsIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """A set counted by the camera: adds to the day's push-ups / squats / sit-ups (the check-in fields),
    keeps the camera's own count, and raises the best set when this one beats it."""
    _check_not_future(db, current_user, day)
    log = daily_logs.get_log(db, current_user, day)
    merged = daily_logs.merged(log).get("body", {}) if log else {}
    body = {payload.exercise: (merged.get(payload.exercise) or 0) + payload.count,
            f"cam_{payload.exercise}": (merged.get(f"cam_{payload.exercise}") or 0) + payload.count}
    if payload.exercise == "pushups":
        body["cam_best_set"] = max(merged.get("cam_best_set") or 0, payload.count)
        if payload.count > (merged.get("max_pushups") or 0):
            body["max_pushups"] = payload.count
    return _to_schema(daily_logs.save(db, current_user, day, "manual", {"body": body}))


@router.post("/batch", response_model=list[DailyLogOut])
def save_logs(
    payload: DailyLogBatchIn,
    source: Source = "manual",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Several days in one request (up to 31), e.g. a phone catching up after being offline."""
    for item in payload.days:
        _check_not_future(db, current_user, item.date)
    if len({item.date for item in payload.days}) != len(payload.days):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Each date may appear only once")
    return [_to_schema(daily_logs.save(db, current_user, item.date, source, _updates(item))) for item in payload.days]


@router.delete("/{day}", status_code=status.HTTP_204_NO_CONTENT)
def delete_log(
    day: date,
    source: Literal["auto", "manual", "all"] = "all",
    section: str | None = None,
    field: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a whole day, or narrow it down: ?source=manual&section=sleep&field=hours removes just
    that correction (the phone's value shows through again)."""
    if field is not None and section is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="`field` needs a `section`")
    if section is not None and section not in DailyLogIn.model_fields:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown section '{section}'")
    if field is not None:
        section_model = DailyLogIn.model_fields[section].annotation.__args__[0]  # SleepLog | None → SleepLog
        if field not in section_model.model_fields:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown field '{section}.{field}'")

    sources = ("auto", "manual") if source == "all" else (source,)
    if not daily_logs.clear(db, current_user, day, sources, section, field):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nothing logged for that day")
