"""achievements, worn titles, profile photos

Revision ID: 0012
Revises: 0011
Create Date: 2026-10-07

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0012"
down_revision: Union[str, None] = "0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "earned_achievements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("key", sa.String(40), nullable=False),
        sa.Column("earned_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "key", name="uq_earned_achievement_user_key"),
    )
    op.create_index("ix_earned_achievements_user_id", "earned_achievements", ["user_id"])
    op.create_table(
        "profile_photos",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("token", sa.String(40), nullable=False, unique=True),
        sa.Column("data", sa.LargeBinary(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    with op.batch_alter_table("user_profiles") as batch:
        batch.add_column(sa.Column("title_key", sa.String(40), nullable=True))
        batch.add_column(sa.Column("achievements_seen_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("share_achievements", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    with op.batch_alter_table("user_profiles") as batch:
        batch.drop_column("share_achievements")
        batch.drop_column("achievements_seen_at")
        batch.drop_column("title_key")
    op.drop_table("profile_photos")
    op.drop_index("ix_earned_achievements_user_id", table_name="earned_achievements")
    op.drop_table("earned_achievements")
