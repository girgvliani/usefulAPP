"""user profiles and goals

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-30

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

goal_type_enum = sa.Enum("weight", "max_pushups", "steps", "sleep", "income", "custom", name="goaltype")


def upgrade() -> None:
    op.create_table(
        "user_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("timezone", sa.String(64), nullable=False),
        sa.Column("pushup_target", sa.Integer(), nullable=False),
        sa.Column("steps_target", sa.Integer(), nullable=False),
        sa.Column("sleep_target", sa.Float(), nullable=False),
        sa.UniqueConstraint("user_id", name="uq_profile_user"),
    )
    op.create_index("ix_user_profiles_user_id", "user_profiles", ["user_id"])

    op.create_table(
        "goals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", goal_type_enum, nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("unit", sa.String(20), nullable=False),
        sa.Column("start_value", sa.Float(), nullable=False),
        sa.Column("target_value", sa.Float(), nullable=False),
        sa.Column("current_value", sa.Float(), nullable=True),
        sa.Column("deadline", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_goals_user_id", "goals", ["user_id"])

    # Accounts that existed before profiles keep how the app behaved for them: 100 push-ups a day, Lari
    op.execute(
        "INSERT INTO user_profiles (user_id, currency, timezone, pushup_target, steps_target, sleep_target) "
        "SELECT id, 'GEL', 'Asia/Tbilisi', 100, 8000, 7.5 FROM users"
    )


def downgrade() -> None:
    op.drop_table("goals")
    op.drop_table("user_profiles")
    goal_type_enum.drop(op.get_bind(), checkfirst=True)
