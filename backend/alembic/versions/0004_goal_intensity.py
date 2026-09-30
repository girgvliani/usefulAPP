"""goggins scale on goals

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-30

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Existing goals start in the middle of the scale
    op.add_column("goals", sa.Column("intensity", sa.Integer(), nullable=False, server_default="5"))


def downgrade() -> None:
    with op.batch_alter_table("goals") as batch:  # batch mode so SQLite can drop the column too
        batch.drop_column("intensity")
