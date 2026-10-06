from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import QuestionnaireAttempt, User
from app.services import character_stats, daily_logs, profiles, questionnaire

router = APIRouter(prefix="/questionnaire", tags=["questionnaire"])

# Peer groups decide classes, which aren't public yet: kept on the server only
HIDDEN = {"cohort"}


class AnswersIn(BaseModel):
    answers: dict


def _public(attempt: QuestionnaireAttempt) -> dict:
    return {
        "id": attempt.id,
        "created_at": attempt.created_at,
        "answers": attempt.answers,
        "results": {k: v for k, v in attempt.results.items() if k not in HIDDEN},
    }


def _latest(db: Session, user: User) -> QuestionnaireAttempt | None:
    return db.scalar(
        select(QuestionnaireAttempt).where(QuestionnaireAttempt.user_id == user.id)
        .order_by(QuestionnaireAttempt.created_at.desc(), QuestionnaireAttempt.id.desc()).limit(1)
    )


def _latest_weight(db: Session, user: User) -> float | None:
    today = profiles.today(db, user)
    for log in reversed(daily_logs.list_logs(db, user, today - timedelta(days=60), today)):
        weight = daily_logs.merged(log).get("body", {}).get("weight_kg")
        if weight is not None:
            return weight
    return None


@router.get("")
def get_questionnaire(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """The questions, answers to start from (your last attempt, then your profile), and your latest results."""
    latest = _latest(db, current_user)
    profile = profiles.get_profile(db, current_user)
    prefill = dict(latest.answers) if latest else {}
    known = {"birth_year": profile.birth_year, "sex": profile.sex, "height_cm": profile.height_cm,
             "weight_kg": _latest_weight(db, current_user)}
    prefill.update({k: v for k, v in known.items() if v is not None})  # what you've logged since beats old answers
    return {**questionnaire.catalog(), "prefill": prefill, "latest": _public(latest) if latest else None}


@router.post("", status_code=status.HTTP_201_CREATED)
def submit(payload: AnswersIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Saves an attempt (every one is kept) and returns your priorities, focus areas and plan.
    Your birth year, sex and height go into your profile and your weight into today's log."""
    try:
        answers = questionnaire.validate(payload.answers)
    except questionnaire.AnswerError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    day = profiles.today(db, current_user)
    profile = profiles.get_profile(db, current_user)
    profile.birth_year, profile.sex, profile.height_cm = answers["birth_year"], answers["sex"], answers["height_cm"]
    if _latest_weight(db, current_user) != answers["weight_kg"]:
        daily_logs.save(db, current_user, day, "manual", {"body": {"weight_kg": answers["weight_kg"]}})

    data = daily_logs.stats_input(db, current_user, day)
    sheet = character_stats.character_sheet(data, day.isoformat(), profile.pushup_target, profile.sleep_target)
    attempt = QuestionnaireAttempt(
        user_id=current_user.id, answers=answers, results=questionnaire.results(answers, sheet["categories"], day)
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return _public(attempt)


@router.get("/attempts")
def list_attempts(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Every attempt, newest first, with its focus areas: how what matters to you has changed."""
    rows = db.scalars(
        select(QuestionnaireAttempt).where(QuestionnaireAttempt.user_id == current_user.id)
        .order_by(QuestionnaireAttempt.created_at.desc(), QuestionnaireAttempt.id.desc())
    )
    return [_public(a) for a in rows]


@router.get("/attempts/{attempt_id}")
def get_attempt(attempt_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    attempt = db.scalar(
        select(QuestionnaireAttempt).where(QuestionnaireAttempt.user_id == current_user.id, QuestionnaireAttempt.id == attempt_id)
    )
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")
    return _public(attempt)
