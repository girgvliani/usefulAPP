"""paths: who you want to become, and the sub-classes a path brings

Revision ID: 0017
Revises: 0016
Create Date: 2026-10-12

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0017"
down_revision: Union[str, None] = "0016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("sub_classes") as batch:
        batch.add_column(sa.Column("path_key", sa.String(20), nullable=True))
        batch.add_column(sa.Column("template_key", sa.String(30), nullable=True))
        batch.add_column(sa.Column("adjusted_at", sa.Date(), nullable=True))
    op.create_table(
        "user_paths",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("path_key", sa.String(20), nullable=False),
        sa.Column("started_on", sa.Date(), nullable=False),
        sa.Column("left_on", sa.Date(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("user_id", "path_key", name="uq_user_path"),
    )
    op.create_index("ix_user_paths_user_id", "user_paths", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_user_paths_user_id", table_name="user_paths")
    op.drop_table("user_paths")
    with op.batch_alter_table("sub_classes") as batch:
        batch.drop_column("adjusted_at")
        batch.drop_column("template_key")
        batch.drop_column("path_key")
