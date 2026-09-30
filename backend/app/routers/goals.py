from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Goal, GoalType, User
from app.schemas import GoalIn, GoalOut, GoalUpdate
from app.services import daily_logs, goals, profiles

router = APIRouter(prefix="/goals", tags=["goals"])


def _owned_goal(db: Session, user: User, goal_id: int) -> Goal:
    goal = db.scalar(select(Goal).where(Goal.user_id == user.id, Goal.id == goal_id))
    if not goal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")
    return goal


def _context(db: Session, user: User) -> tuple[dict, str]:
    """The user's recent logs, loaded once for every goal in a response."""
    day = profiles.today(db, user)
    return daily_logs.stats_input(db, user, day), day.isoformat()


def _to_schema(goal: Goal, data: dict, day: str) -> GoalOut:
    current = goals.current_value(goal, data, day)
    progress = goals.progress(goal.start_value, goal.target_value, current)
    return GoalOut(
        id=goal.id,
        type=goal.type.value,
        title=goal.title,
        unit=goal.unit,
        start_value=goal.start_value,
        target_value=goal.target_value,
        current_value=current,
        progress=progress,
        direction="decrease" if goal.target_value < goal.start_value else "increase",
        achieved=progress == 1,
        deadline=goal.deadline,
        intensity=goal.intensity,
        created_at=goal.created_at,
    )


@router.get("", response_model=list[GoalOut])
def list_goals(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    data, day = _context(db, current_user)
    rows = db.scalars(select(Goal).where(Goal.user_id == current_user.id).order_by(Goal.created_at))
    return [_to_schema(goal, data, day) for goal in rows]


@router.post("", response_model=GoalOut, status_code=status.HTTP_201_CREATED)
def create_goal(payload: GoalIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Leave start_value out to start from your latest logged value (e.g. today's weight)."""
    goal_type = GoalType(payload.type)
    if goal_type != GoalType.custom and payload.current_value is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only custom goals take a current_value")

    data, day = _context(db, current_user)
    goal = Goal(user_id=current_user.id, type=goal_type, target_value=payload.target_value, current_value=payload.current_value)
    start = payload.start_value
    if start is None:
        start = payload.current_value if goal_type == GoalType.custom else goals.current_value(goal, data, day)
    if start is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Nothing logged yet to start from; send start_value"
        )
    if start == payload.target_value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Start and target are the same")

    goal.start_value = start
    goal.unit = payload.unit or goals.unit_for(goal_type, profiles.get_profile(db, current_user).currency)
    goal.title = payload.title or f"{goals.LABELS[goal_type]}: {start:g} → {payload.target_value:g} {goal.unit}".strip()
    goal.deadline = payload.deadline
    goal.intensity = payload.intensity
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return _to_schema(goal, data, day)


@router.get("/{goal_id}", response_model=GoalOut)
def get_goal(goal_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    goal = _owned_goal(db, current_user, goal_id)
    return _to_schema(goal, *_context(db, current_user))


@router.patch("/{goal_id}", response_model=GoalOut)
def update_goal(
    goal_id: int, payload: GoalUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    goal = _owned_goal(db, current_user, goal_id)
    changes = payload.model_dump(exclude_none=True)
    if "current_value" in changes and goal.type != GoalType.custom:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only custom goals take a current_value")
    if changes.get("start_value", goal.start_value) == changes.get("target_value", goal.target_value):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Start and target are the same")
    for field, value in changes.items():
        setattr(goal, field, value)
    db.commit()
    db.refresh(goal)
    return _to_schema(goal, *_context(db, current_user))


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_goal(goal_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.delete(_owned_goal(db, current_user, goal_id))
    db.commit()
