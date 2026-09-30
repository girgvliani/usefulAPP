"""meals and body profile fields

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-30

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("user_profiles", sa.Column("height_cm", sa.Float(), nullable=True))
    op.add_column("user_profiles", sa.Column("birth_year", sa.Integer(), nullable=True))
    op.add_column("user_profiles", sa.Column("sex", sa.String(6), nullable=True))

    op.create_table(
        "meals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("eaten_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("meal_type", sa.String(10), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("items", sa.JSON(), nullable=False),
        sa.Column("kcal", sa.Float(), nullable=False),
        sa.Column("protein", sa.Float(), nullable=False),
        sa.Column("carbs", sa.Float(), nullable=False),
        sa.Column("fat", sa.Float(), nullable=False),
        sa.Column("source", sa.String(12), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_meals_user_id", "meals", ["user_id"])
    op.create_index("ix_meals_date", "meals", ["date"])


def downgrade() -> None:
    op.drop_table("meals")
    with op.batch_alter_table("user_profiles") as batch:  # batch mode so SQLite can drop columns too
        batch.drop_column("sex")
        batch.drop_column("birth_year")
        batch.drop_column("height_cm")
