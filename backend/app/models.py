import enum
from datetime import date, datetime

from sqlalchemy import (
    LargeBinary,
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class HabitType(str, enum.Enum):
    shower = "shower"
    workout = "workout"


class GoalType(str, enum.Enum):
    weight = "weight"            # kg, from logged weight
    max_pushups = "max_pushups"  # reps in one set, from push-up tests
    steps = "steps"              # 7-day average steps
    sleep = "sleep"              # 7-day average hours
    income = "income"            # this month's earnings
    custom = "custom"            # anything else; current value entered by hand


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    last_login: Mapped[date] = mapped_column(Date, server_default=func.current_date())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    life_areas: Mapped[list["LifeArea"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    habits: Mapped[list["Habit"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    projects: Mapped[list["Project"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    todos: Mapped[list["Todo"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    milestones: Mapped[list["EpicMilestone"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class LifeArea(Base):
    __tablename__ = "life_areas"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_life_area_user_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    level: Mapped[int] = mapped_column(Integer, default=1)
    xp: Mapped[int] = mapped_column(Integer, default=0)
    last_active: Mapped[date] = mapped_column(Date, server_default=func.current_date())

    user: Mapped["User"] = relationship(back_populates="life_areas")


class Habit(Base):
    __tablename__ = "habits"
    __table_args__ = (UniqueConstraint("user_id", "type", name="uq_habit_user_type"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    type: Mapped[HabitType] = mapped_column(Enum(HabitType), nullable=False)
    streak: Mapped[int] = mapped_column(Integer, default=0)
    last_done: Mapped[date | None] = mapped_column(Date, nullable=True)

    user: Mapped["User"] = relationship(back_populates="habits")


class PushupLog(Base):
    __tablename__ = "pushup_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    date: Mapped[date] = mapped_column(Date, server_default=func.current_date())
    count: Mapped[int] = mapped_column(Integer, nullable=False)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    value: Mapped[int] = mapped_column(Integer, nullable=False)
    deadline: Mapped[date] = mapped_column(Date, nullable=False)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    completion_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[date] = mapped_column(Date, server_default=func.current_date())

    user: Mapped["User"] = relationship(back_populates="projects")


class Todo(Base):
    __tablename__ = "todos"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    area_id: Mapped[int] = mapped_column(ForeignKey("life_areas.id", ondelete="CASCADE"), nullable=False)
    task: Mapped[str] = mapped_column(String(300), nullable=False)
    base_xp: Mapped[int] = mapped_column(Integer, nullable=False)
    deadline: Mapped[date] = mapped_column(Date, nullable=False)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    completion_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[date] = mapped_column(Date, server_default=func.current_date())

    user: Mapped["User"] = relationship(back_populates="todos")
    area: Mapped["LifeArea"] = relationship()


class EpicMilestone(Base):
    __tablename__ = "epic_milestones"
    __table_args__ = (UniqueConstraint("user_id", "key", name="uq_milestone_user_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(300), nullable=False)
    xp_reward: Mapped[int] = mapped_column(Integer, nullable=False)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped["User"] = relationship(back_populates="milestones")


class ScreenTimeLog(Base):
    __tablename__ = "screen_time_logs"
    __table_args__ = (UniqueConstraint("user_id", "date", name="uq_screen_time_user_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    date: Mapped[date] = mapped_column(Date, server_default=func.current_date())
    hours: Mapped[float] = mapped_column(Float, nullable=False)


class SocialInteraction(Base):
    __tablename__ = "social_interactions"
    __table_args__ = (UniqueConstraint("user_id", name="uq_social_user"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    week_start: Mapped[date] = mapped_column(Date, server_default=func.current_date())
    weekly_count: Mapped[int] = mapped_column(Integer, default=0)


class Income(Base):
    __tablename__ = "income"
    __table_args__ = (UniqueConstraint("user_id", name="uq_income_user"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    monthly_goal: Mapped[int] = mapped_column(Integer, default=10000)
    current_month_earnings: Mapped[int] = mapped_column(Integer, default=0)
    target_month: Mapped[str] = mapped_column(String(7), default="")


class DailyScore(Base):
    __tablename__ = "daily_scores"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    date: Mapped[date] = mapped_column(Date, server_default=func.current_date())
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    grade: Mapped[str] = mapped_column(String(5), nullable=False)


class Achievement(Base):
    __tablename__ = "achievements"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    unlocked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DailyLog(Base):
    """One row per user per day, shaped like the check-in: {section: {field: value}}.
    `auto` is written by devices (phone sync), `manual` by check-ins; manual wins per field."""
    __tablename__ = "daily_logs"
    __table_args__ = (UniqueConstraint("user_id", "date", name="uq_daily_log_user_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    auto: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    manual: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class DeviceToken(Base):
    """Long-lived token for something that syncs without a login, like the phone app.
    Only the SHA-256 of the token is stored; the token itself is shown once."""
    __tablename__ = "device_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class UserProfile(Base):
    """Personal settings. The stat formulas are the same for everyone; these targets are each user's own."""
    __tablename__ = "user_profiles"
    __table_args__ = (UniqueConstraint("user_id", name="uq_profile_user"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False)
    pushup_target: Mapped[int] = mapped_column(Integer, nullable=False)  # push-ups a day
    steps_target: Mapped[int] = mapped_column(Integer, nullable=False)   # steps a day
    sleep_target: Mapped[float] = mapped_column(Float, nullable=False)   # hours a night; sets MP's sleep debt
    # For the calorie target (Mifflin-St Jeor); weight comes from the daily logs
    height_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    birth_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sex: Mapped[str | None] = mapped_column(String(6), nullable=True)  # "male" / "female"
    # Friends: a code to share, and what friends may see (all off until the user turns it on)
    friend_code: Mapped[str | None] = mapped_column(String(12), unique=True, nullable=True)
    share_level: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    share_stats: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    share_streaks: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    share_goals: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    # How others (friends, the global leaderboard) see you: "name", "nickname" or "code"
    nickname: Mapped[str | None] = mapped_column(String(40), nullable=True)
    public_name: Mapped[str] = mapped_column(String(10), nullable=False, default="nickname", server_default="nickname")
    # Dave Ramsey's Baby Steps: the numbers the user enters (services/baby_steps.py)
    baby_steps: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict, server_default="{}")
    # Achievements: the title worn (an achievement key), when the unlock screen was last seen, and
    # whether friends see your badges
    title_key: Mapped[str | None] = mapped_column(String(40), nullable=True)
    # The one earned badge shown on the corner of your profile photo (an achievement key), if you pick one
    badge_key: Mapped[str | None] = mapped_column(String(40), nullable=True)
    achievements_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    share_achievements: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    # Customization unlocked by level: {"off": {"MP": ["Meditation"]}, ...}
    customization: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict, server_default="{}")
    # Chrome history import: site -> category the user chose ("localhost:3000" -> "work")
    site_groups: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict, server_default="{}")
    # The global leaderboard (name, level, title, XP): everyone is on it unless they hide
    on_leaderboard: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")


class Friendship(Base):
    """A friend request, and once accepted, a friendship. One row per pair, either direction."""
    __tablename__ = "friendships"
    __table_args__ = (UniqueConstraint("requester_id", "addressee_id", name="uq_friendship_pair"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    requester_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    addressee_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="pending")  # pending / accepted
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Goal(Base):
    """An outcome to reach. Losing (95 -> 85 kg) and gaining (70 -> 80 kg) use the same row:
    the direction comes from start vs target."""
    __tablename__ = "goals"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    type: Mapped[GoalType] = mapped_column(Enum(GoalType), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    start_value: Mapped[float] = mapped_column(Float, nullable=False)
    target_value: Mapped[float] = mapped_column(Float, nullable=False)
    current_value: Mapped[float | None] = mapped_column(Float, nullable=True)  # custom goals only
    # Goggins scale: how hard to go after it, 1-10. At 8+ the phone app nags you off distracting apps.
    intensity: Mapped[int] = mapped_column(Integer, nullable=False, default=5, server_default="5")
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Meal(Base):
    """One meal, usually from a photo the AI read. Totals are the sum of `items`."""
    __tablename__ = "meals"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    date: Mapped[date] = mapped_column(Date, index=True, nullable=False)  # the user's local day
    eaten_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    meal_type: Mapped[str] = mapped_column(String(10), nullable=False)  # breakfast / lunch / dinner / snack
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    items: Mapped[list] = mapped_column(JSON, default=list, nullable=False)  # [{name, grams, kcal, protein, carbs, fat}]
    kcal: Mapped[float] = mapped_column(Float, nullable=False)
    protein: Mapped[float] = mapped_column(Float, nullable=False)
    carbs: Mapped[float] = mapped_column(Float, nullable=False)
    fat: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(String(12), nullable=False)  # photo / manual
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)  # the AI's own 0-1 estimate
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class QuestionnaireAttempt(Base):
    """One run through the questionnaire. Every attempt is kept; the newest one counts.
    `results` holds what the server worked out from the answers, including the hidden peer group."""
    __tablename__ = "questionnaire_attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    answers: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)  # question id -> answer
    results: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)  # priorities, focus, plan, cohort
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EarnedAchievement(Base):
    """An achievement from services/achievements.py, once reached (the older `achievements` table holds
    the per-skill tier names)"""
    __tablename__ = "earned_achievements"
    __table_args__ = (UniqueConstraint("user_id", "key", name="uq_earned_achievement_user_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    key: Mapped[str] = mapped_column(String(40), nullable=False)
    earned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class ProfilePhoto(Base):
    """A 256 px JPEG, re-encoded on upload (no EXIF, so no location). Served at /photos/{token}.jpg: the
    random token is the only key, and it changes with every upload."""
    __tablename__ = "profile_photos"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    token: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Fast(Base):
    """A fast: intermittent (a daily eating window) or extended (24 h or more). Running while ended_at
    is empty; only one runs at a time (services/fasting.py)."""
    __tablename__ = "fasts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    kind: Mapped[str] = mapped_column(String(12), nullable=False)  # intermittent / extended
    goal_hours: Mapped[float] = mapped_column(Float, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    note: Mapped[str | None] = mapped_column(String(200), nullable=True)


class Subscription(Base):
    """A subscription or recurring bill (services/finances.py). due_day keeps monthly dates on their day
    of the month (the 31st stays the 31st after February)."""
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    cycle: Mapped[str] = mapped_column(String(10), nullable=False)  # weekly / monthly / quarterly / yearly
    next_due: Mapped[date] = mapped_column(Date, nullable=False)
    due_day: Mapped[int] = mapped_column(Integer, nullable=False)
    category: Mapped[str | None] = mapped_column(String(40), nullable=True)
    note: Mapped[str | None] = mapped_column(String(200), nullable=True)
    autopay: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    remind_days: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    last_paid: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SubClass(Base):
    """A sub-class a person made inside one of the six classes (services/sub_classes.py). The nine
    standard stats are the built-in sub-classes; these are each person's own, fed by one measure."""
    __tablename__ = "sub_classes"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    class_key: Mapped[str] = mapped_column(String(12), nullable=False)  # mental / physical / practical / cultural / discipline / social
    name: Mapped[str] = mapped_column(String(40), nullable=False)
    icon: Mapped[str | None] = mapped_column(String(8), nullable=True)
    # number / yesno / rating (1-5, self-rated) are answered in the check-in; field reads a day-log value
    kind: Mapped[str] = mapped_column(String(10), nullable=False)
    field: Mapped[str | None] = mapped_column(String(40), nullable=True)  # "body.steps" for kind field
    unit: Mapped[str | None] = mapped_column(String(16), nullable=True)
    target: Mapped[float | None] = mapped_column(Float, nullable=True)
    period: Mapped[str] = mapped_column(String(5), nullable=False, default="day")  # day / week
    better: Mapped[str] = mapped_column(String(4), nullable=False, default="more")  # more / less
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Made by a path (services/paths.py): which path and which of its sub-classes; None for your own
    path_key: Mapped[str | None] = mapped_column(String(20), nullable=True)
    template_key: Mapped[str | None] = mapped_column(String(30), nullable=True)
    adjusted_at: Mapped[date | None] = mapped_column(Date, nullable=True)  # last weekly target adjustment
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class UserPath(Base):
    """A path someone is on: who they want to become (services/paths.py). Leaving keeps the row and the
    history; XP counts from started_on."""
    __tablename__ = "user_paths"
    __table_args__ = (UniqueConstraint("user_id", "path_key", name="uq_user_path"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    path_key: Mapped[str] = mapped_column(String(20), nullable=False)
    started_on: Mapped[date] = mapped_column(Date, nullable=False)
    left_on: Mapped[date | None] = mapped_column(Date, nullable=True)  # XP earned until then stays
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class UserBook(Base):
    """A book someone has (services/books.py): unlocked by a path level or gifted by a friend, and which
    chapters they've read ({index: day})."""
    __tablename__ = "user_books"
    __table_args__ = (UniqueConstraint("user_id", "book_key", name="uq_user_book"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    book_key: Mapped[str] = mapped_column(String(30), nullable=False)
    via: Mapped[str] = mapped_column(String(10), nullable=False)  # level / gift
    gifted_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True)
    unlocked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    chapters_read: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class BookEntry(Base):
    """One thing logged in a book's tracker: a palace, a recall test, a card, a focus session, a decision…
    The fields depend on the kind (books.ENTRY_FIELDS)."""
    __tablename__ = "book_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    book_key: Mapped[str] = mapped_column(String(30), nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    day: Mapped[date] = mapped_column(Date, nullable=False)
    data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
