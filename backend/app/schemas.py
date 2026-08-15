from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ---- Auth ----

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---- Life areas ----

class LifeAreaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    level: int
    xp: int
    last_active: date


# ---- XP results ----

class XpResult(BaseModel):
    area: LifeAreaOut
    leveled_up: bool
    achievement: str | None


# ---- Habits ----

class PushupIn(BaseModel):
    count: int = Field(ge=0, le=5000)


class WorkoutResult(BaseModel):
    met_requirement: bool
    streak: int
    bonus_xp: int
    consistency_bonus: int
    xp_result: XpResult | None


class ShowerResult(BaseModel):
    already_logged: bool
    streak: int
    xp_result: XpResult | None = None


class ScreenTimeResult(BaseModel):
    over_limit: bool
    penalty: int


class SocialResult(BaseModel):
    over_limit: bool
    count: int
    penalty: int | None = None
    xp_result: XpResult | None = None


class SleepIn(BaseModel):
    hours: float = Field(ge=0, le=24)


class ScreenTimeIn(BaseModel):
    hours: float = Field(ge=0, le=24)


# ---- Projects ----

class ProjectIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    value: int = Field(gt=0)
    deadline: date


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    value: int
    deadline: date
    completed: bool
    completion_date: date | None
    created_at: date


# ---- Todos ----

class TodoIn(BaseModel):
    task: str = Field(min_length=1, max_length=300)
    area_id: int
    base_xp: int = Field(ge=0, le=10000)
    deadline: date


class TodoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    task: str
    area_id: int
    base_xp: int
    deadline: date
    completed: bool
    completion_date: date | None
    created_at: date


# ---- Milestones ----

class MilestoneOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    key: str
    description: str
    xp_reward: int
    completed: bool


# ---- Income ----

class IncomeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    monthly_goal: int
    current_month_earnings: int
    target_month: str


class IncomeUpdate(BaseModel):
    current_month_earnings: int | None = Field(default=None, ge=0)
    monthly_goal: int | None = Field(default=None, gt=0)
    target_month: str | None = Field(default=None, max_length=7)


# ---- Manual XP ----

class ManualXpIn(BaseModel):
    area_id: int
    xp: int = Field(ge=-100000, le=100000)
    reason: str = Field(default="", max_length=200)


# ---- Stats / dashboard ----

class HabitStatus(BaseModel):
    type: str
    streak: int
    done_today: bool


class DailyScoreOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    date: date
    score: int
    grade: str


class StatsOut(BaseModel):
    life_areas: list[LifeAreaOut]
    habits: list[HabitStatus]
    income: IncomeOut
    milestones: list[MilestoneOut]
    todays_score: DailyScoreOut | None
