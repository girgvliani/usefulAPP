"""nicknames and how others see you; Baby Steps

Revision ID: 0011
Revises: 0010
Create Date: 2026-10-07

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("user_profiles") as batch:
        batch.add_column(sa.Column("nickname", sa.String(40), nullable=True))
        # Others see a nickname (or the friend code until one is set), not a real name, unless chosen
        batch.add_column(sa.Column("public_name", sa.String(10), nullable=False, server_default="nickname"))
        batch.add_column(sa.Column("baby_steps", sa.JSON(), nullable=False, server_default="{}"))


def downgrade() -> None:
    with op.batch_alter_table("user_profiles") as batch:
        batch.drop_column("baby_steps")
        batch.drop_column("public_name")
        batch.drop_column("nickname")
