"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-08-15

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

habit_type_enum = sa.Enum("shower", "workout", name="habittype")


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("last_login", sa.Date(), server_default=sa.text("CURRENT_DATE")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "life_areas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("level", sa.Integer(), server_default="1"),
        sa.Column("xp", sa.Integer(), server_default="0"),
        sa.Column("last_active", sa.Date(), server_default=sa.text("CURRENT_DATE")),
        sa.UniqueConstraint("user_id", "name", name="uq_life_area_user_name"),
    )
    op.create_index("ix_life_areas_user_id", "life_areas", ["user_id"])

    op.create_table(
        "habits",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", habit_type_enum, nullable=False),
        sa.Column("streak", sa.Integer(), server_default="0"),
        sa.Column("last_done", sa.Date(), nullable=True),
        sa.UniqueConstraint("user_id", "type", name="uq_habit_user_type"),
    )
    op.create_index("ix_habits_user_id", "habits", ["user_id"])

    op.create_table(
        "pushup_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("date", sa.Date(), server_default=sa.text("CURRENT_DATE")),
        sa.Column("count", sa.Integer(), nullable=False),
    )
    op.create_index("ix_pushup_logs_user_id", "pushup_logs", ["user_id"])

    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("value", sa.Integer(), nullable=False),
        sa.Column("deadline", sa.Date(), nullable=False),
        sa.Column("completed", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("completion_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.Date(), server_default=sa.text("CURRENT_DATE")),
    )
    op.create_index("ix_projects_user_id", "projects", ["user_id"])

    op.create_table(
        "todos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("area_id", sa.Integer(), sa.ForeignKey("life_areas.id", ondelete="CASCADE"), nullable=False),
        sa.Column("task", sa.String(300), nullable=False),
        sa.Column("base_xp", sa.Integer(), nullable=False),
        sa.Column("deadline", sa.Date(), nullable=False),
        sa.Column("completed", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("completion_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.Date(), server_default=sa.text("CURRENT_DATE")),
    )
    op.create_index("ix_todos_user_id", "todos", ["user_id"])

    op.create_table(
        "epic_milestones",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("key", sa.String(100), nullable=False),
        sa.Column("description", sa.String(300), nullable=False),
        sa.Column("xp_reward", sa.Integer(), nullable=False),
        sa.Column("completed", sa.Boolean(), server_default=sa.text("false")),
        sa.UniqueConstraint("user_id", "key", name="uq_milestone_user_key"),
    )
    op.create_index("ix_epic_milestones_user_id", "epic_milestones", ["user_id"])

    op.create_table(
        "screen_time_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("date", sa.Date(), server_default=sa.text("CURRENT_DATE")),
        sa.Column("hours", sa.Float(), nullable=False),
        sa.UniqueConstraint("user_id", "date", name="uq_screen_time_user_date"),
    )
    op.create_index("ix_screen_time_logs_user_id", "screen_time_logs", ["user_id"])

    op.create_table(
        "social_interactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("week_start", sa.Date(), server_default=sa.text("CURRENT_DATE")),
        sa.Column("weekly_count", sa.Integer(), server_default="0"),
        sa.UniqueConstraint("user_id", name="uq_social_user"),
    )
    op.create_index("ix_social_interactions_user_id", "social_interactions", ["user_id"])

    op.create_table(
        "income",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("monthly_goal", sa.Integer(), server_default="10000"),
        sa.Column("current_month_earnings", sa.Integer(), server_default="0"),
        sa.Column("target_month", sa.String(7), server_default=""),
        sa.UniqueConstraint("user_id", name="uq_income_user"),
    )
    op.create_index("ix_income_user_id", "income", ["user_id"])

    op.create_table(
        "daily_scores",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("date", sa.Date(), server_default=sa.text("CURRENT_DATE")),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("grade", sa.String(5), nullable=False),
    )
    op.create_index("ix_daily_scores_user_id", "daily_scores", ["user_id"])

    op.create_table(
        "achievements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("unlocked_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_achievements_user_id", "achievements", ["user_id"])


def downgrade() -> None:
    op.drop_table("achievements")
    op.drop_table("daily_scores")
    op.drop_table("income")
    op.drop_table("social_interactions")
    op.drop_table("screen_time_logs")
    op.drop_table("epic_milestones")
    op.drop_table("todos")
    op.drop_table("projects")
    op.drop_table("pushup_logs")
    op.drop_table("habits")
    op.drop_table("life_areas")
    op.drop_table("users")
    habit_type_enum.drop(op.get_bind(), checkfirst=True)
