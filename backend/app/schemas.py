from datetime import date, datetime
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


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


class LifeAreaIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)


# ---- XP results ----

class XpResult(BaseModel):
    area: LifeAreaOut
    leveled_up: bool
    achievement: str | None


# ---- Habits ----

class PushupIn(BaseModel):
    count: int = Field(ge=0, le=5000)


class PushupLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    date: date
    count: int


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


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    value: int | None = Field(default=None, gt=0)
    deadline: date | None = None


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


class TodoUpdate(BaseModel):
    task: str | None = Field(default=None, min_length=1, max_length=300)
    area_id: int | None = None
    base_xp: int | None = Field(default=None, ge=0, le=10000)
    deadline: date | None = None


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


class MilestoneIn(BaseModel):
    description: str = Field(min_length=1, max_length=300)
    xp_reward: int = Field(ge=0, le=100_000)


class MilestoneUpdate(BaseModel):
    description: str | None = Field(default=None, min_length=1, max_length=300)
    xp_reward: int | None = Field(default=None, ge=0, le=100_000)


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


# ---- Devices ----

class DeviceIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class DeviceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    created_at: datetime
    last_used_at: datetime | None


class DeviceCreated(DeviceOut):
    token: str  # shown once; only its hash is stored


# ---- Daily logs ----
# Same sections and fields as the terminal check-in. Every field is optional:
# a sync or check-in only sends what it knows, and None never overwrites.

HHMM = r"^([01]\d|2[0-3]):[0-5]\d$"


def minutes():
    return Field(default=None, ge=0, le=1440)



class LogSection(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SleepLog(LogSection):
    bed: str | None = Field(default=None, pattern=HHMM)
    wake: str | None = Field(default=None, pattern=HHMM)
    hours: float | None = Field(default=None, ge=0, le=24)
    quality: float | None = Field(default=None, ge=0, le=100)
    alcohol: int | None = Field(default=None, ge=0, le=50)
    late_caffeine: bool | None = None
    screen_before_bed: bool | None = None
    estimated: bool | None = None  # guessed from phone usage, not measured by a wearable


class WorkLog(LogSection):
    total: float | None = Field(default=None, ge=0, le=24)
    deep: float | None = Field(default=None, ge=0, le=24)


class MindLog(LogSection):
    learning_min: int | None = minutes()
    meditation_min: int | None = minutes()


class ScreenLog(LogSection):
    short_video_min: int | None = minutes()
    long_video_min: int | None = minutes()
    gaming_min: int | None = minutes()
    social_min: int | None = minutes()  # social feeds (Instagram, TikTok, Facebook, X, Snapchat, Reddit…)
    total_min: int | None = minutes()   # all phone screen time except the home screen
    night_min: int | None = minutes()   # phone use between midnight and 5am
    unlocks: int | None = Field(default=None, ge=0, le=5000)
    apps: dict[str, int] | None = None  # raw minutes per app package, kept for re-categorizing later


class BodyLog(LogSection):
    steps: int | None = Field(default=None, ge=0, le=200_000)
    active_min: int | None = minutes()
    pushups: int | None = Field(default=None, ge=0, le=5000)
    max_pushups: int | None = Field(default=None, ge=0, le=1000)
    strength: bool | None = None
    outdoor_min: int | None = minutes()
    shower: bool | None = None
    weight_kg: float | None = Field(default=None, ge=20, le=400)
    resting_hr: int | None = Field(default=None, ge=20, le=250)


class SocialLog(LogSection):
    interactions: int | None = Field(default=None, ge=0, le=100)


class BrowserLog(LogSection):
    """Estimated minutes per category from an imported Chrome history (time until the next visit, at most 10 min)"""
    work_min: int | None = minutes()
    learning_min: int | None = minutes()
    social_min: int | None = minutes()
    entertainment_min: int | None = minutes()
    shopping_min: int | None = minutes()
    news_min: int | None = minutes()
    other_min: int | None = minutes()
    visits: int | None = Field(default=None, ge=0, le=100_000)
    searches: int | None = Field(default=None, ge=0, le=100_000)
    shorts: int | None = Field(default=None, ge=0, le=100_000)  # YouTube Shorts opened in the browser


class DailyLogIn(LogSection):
    sleep: SleepLog | None = None
    work: WorkLog | None = None
    mind: MindLog | None = None
    screen: ScreenLog | None = None
    body: BodyLog | None = None
    social: SocialLog | None = None
    browser: BrowserLog | None = None


class DailyLogBatchItem(DailyLogIn):
    date: date


class DailyLogBatchIn(LogSection):
    days: list[DailyLogBatchItem] = Field(min_length=1, max_length=31)


class DailyLogOut(BaseModel):
    date: date
    auto: dict
    manual: dict
    merged: dict  # what the stats use: auto, overridden field by field by manual
    updated_at: datetime | None


# ---- Character sheet ----

class StatComponent(BaseModel):
    name: str
    weight: float
    score: float | None
    note: str


class StatPenalty(BaseModel):
    name: str
    points: float
    note: str


class BestMove(BaseModel):
    name: str
    points: int


class StatResult(BaseModel):
    code: str
    name: str
    score: int | None
    grade: str | None
    confidence: int
    ceiling: int | None
    ceiling_note: str
    best_move: BestMove | None
    components: list[StatComponent]
    penalties: list[StatPenalty]
    off: list[str] = []  # parts the user turned off (customization)


class CategoryResult(BaseModel):
    """One of the six areas: the average of its stats that have data."""
    key: str
    name: str
    score: int | None
    grade: str | None
    stats: list[str]  # stat codes, in display order


class CharacterSheetOut(BaseModel):
    date: date
    overall: int | None  # average of the categories that have data
    overall_grade: str | None
    categories: list[CategoryResult]
    stats: list[StatResult]


class CharacterDay(BaseModel):
    """One point of stat history: the scores only, for charts."""
    date: date
    overall: int | None
    scores: dict[str, int | None]
    categories: dict[str, int | None] = {}


# ---- Profile ----

class ProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    display_name: str | None
    nickname: str | None = None
    public_name: Literal["name", "nickname", "code"] = "nickname"  # what friends and the leaderboard see
    currency: str
    timezone: str
    pushup_target: int
    steps_target: int
    sleep_target: float
    height_cm: float | None
    birth_year: int | None
    sex: Literal["male", "female"] | None


class ProfileUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=100)
    nickname: str | None = Field(default=None, min_length=1, max_length=40)
    public_name: Literal["name", "nickname", "code"] | None = None
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")  # ISO code, e.g. GEL, USD, EUR
    timezone: str | None = Field(default=None, max_length=64)
    pushup_target: int | None = Field(default=None, ge=1, le=1000)
    steps_target: int | None = Field(default=None, ge=1000, le=50_000)
    sleep_target: float | None = Field(default=None, ge=5, le=11)
    height_cm: float | None = Field(default=None, ge=100, le=250)
    birth_year: int | None = Field(default=None, ge=1920, le=2020)
    sex: Literal["male", "female"] | None = None

    @field_validator("timezone")
    @classmethod
    def known_timezone(cls, value: str | None) -> str | None:
        if value is not None:
            try:
                ZoneInfo(value)
            except (ZoneInfoNotFoundError, ValueError):
                raise ValueError("Unknown timezone; use a name like Asia/Tbilisi or Europe/London")
        return value


# ---- Goals ----

GoalTypeName = Literal["weight", "max_pushups", "steps", "sleep", "income", "custom"]


class GoalIn(BaseModel):
    type: GoalTypeName
    target_value: float
    start_value: float | None = None  # defaults to your latest logged value
    current_value: float | None = None  # custom goals only
    title: str | None = Field(default=None, min_length=1, max_length=200)
    unit: str | None = Field(default=None, min_length=1, max_length=20)
    deadline: date | None = None
    intensity: int = Field(default=5, ge=1, le=10)  # Goggins scale


class GoalUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    start_value: float | None = None
    target_value: float | None = None
    current_value: float | None = None
    deadline: date | None = None
    intensity: int | None = Field(default=None, ge=1, le=10)


class GoalOut(BaseModel):
    id: int
    type: GoalTypeName
    title: str
    unit: str
    start_value: float
    target_value: float
    current_value: float | None  # None until something is logged
    progress: float | None  # 0 at start, 1 at target
    direction: Literal["increase", "decrease"]
    achieved: bool
    deadline: date | None
    intensity: int
    created_at: datetime


# ---- Streaks ----

class StreakOut(BaseModel):
    key: str
    name: str
    emoji: str
    rule: str  # what keeps it going, e.g. "100+ push-ups"
    current: int
    best: int
    done_today: bool
    at_risk: bool  # going, but not kept today yet: breaks at midnight
    broken_today: bool  # today already went over the limit (reels, sleep): ends tonight whatever you do


class StreaksOut(BaseModel):
    date: date
    mood: Literal["happy", "worried", "angry", "idle"]  # angry = a streak at risk in the evening
    message: str
    streaks: list[StreakOut]


# ---- Meals ----

MealType = Literal["breakfast", "lunch", "dinner", "snack"]


class MealItem(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    grams: float | None = Field(default=None, ge=0, le=5000)
    kcal: float = Field(ge=0, le=10_000)
    protein: float = Field(default=0, ge=0, le=1000)
    carbs: float = Field(default=0, ge=0, le=1000)
    fat: float = Field(default=0, ge=0, le=1000)


class MealIn(BaseModel):
    """A meal typed in by hand, or a corrected one. Totals come from the items."""
    name: str = Field(min_length=1, max_length=200)
    items: list[MealItem] = Field(min_length=1, max_length=30)
    eaten_at: datetime | None = None  # default: now
    meal_type: MealType | None = None  # default: from the time of day


class MealUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    items: list[MealItem] | None = Field(default=None, min_length=1, max_length=30)
    meal_type: MealType | None = None


class MealOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    date: date
    eaten_at: datetime
    meal_type: str
    name: str
    items: list[MealItem]
    kcal: float
    protein: float
    carbs: float
    fat: float
    source: str
    confidence: float | None


class NutritionTargets(BaseModel):
    calories: int | None  # None until height, birth year, sex and a weight are known
    protein: int | None
    bmr: int | None
    tdee: int | None
    adjustment: int  # -500 while losing, +300 while gaining
    missing: list[str]  # what the profile still needs for a calorie target


class DayMeals(BaseModel):
    date: date
    meals: list[MealOut]
    kcal: float
    protein: float
    carbs: float
    fat: float
    targets: NutritionTargets


# ---- Global level ----

class XpItem(BaseModel):
    reason: str
    xp: int


class XpDay(BaseModel):
    date: date
    xp: int


class LevelOut(BaseModel):
    level: int  # starts at 0
    title: str  # Novice, Apprentice, Adept, ... a new one every few levels
    next_title: str | None  # e.g. "Adept at LV 10"; None at the top
    xp: int  # all XP ever: quests + daily activity + goals reached
    level_start_xp: int  # XP where this level began
    next_level_xp: int  # XP where the next one begins
    today_xp: int
    today: list[XpItem]
    sources: dict[str, int]  # activity / quests / goals
    history: list[XpDay]  # activity XP per day, last 30 days, oldest first
