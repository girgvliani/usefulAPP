"""sub-classes: each person's own stats inside the six classes

Revision ID: 0016
Revises: 0015
Create Date: 2026-10-12

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0016"
down_revision: Union[str, None] = "0015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sub_classes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("class_key", sa.String(12), nullable=False),
        sa.Column("name", sa.String(40), nullable=False),
        sa.Column("icon", sa.String(8), nullable=True),
        sa.Column("kind", sa.String(10), nullable=False),
        sa.Column("field", sa.String(40), nullable=True),
        sa.Column("unit", sa.String(16), nullable=True),
        sa.Column("target", sa.Float(), nullable=True),
        sa.Column("period", sa.String(5), nullable=False, server_default="day"),
        sa.Column("better", sa.String(4), nullable=False, server_default="more"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_sub_classes_user_id", "sub_classes", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_sub_classes_user_id", table_name="sub_classes")
    op.drop_table("sub_classes")
