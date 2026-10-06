"""friends: friend codes, sharing switches, friendships

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-07

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SHARES = ("share_level", "share_stats", "share_streaks", "share_goals")


def upgrade() -> None:
    with op.batch_alter_table("user_profiles") as batch:
        batch.add_column(sa.Column("friend_code", sa.String(12), nullable=True))
        for name in SHARES:
            # Nothing is shared until the user chooses to
            batch.add_column(sa.Column(name, sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.create_unique_constraint("uq_profile_friend_code", ["friend_code"])

    op.create_table(
        "friendships",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("requester_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("addressee_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(10), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("requester_id", "addressee_id", name="uq_friendship_pair"),
    )
    op.create_index("ix_friendships_requester_id", "friendships", ["requester_id"])
    op.create_index("ix_friendships_addressee_id", "friendships", ["addressee_id"])


def downgrade() -> None:
    op.drop_table("friendships")
    with op.batch_alter_table("user_profiles") as batch:
        batch.drop_constraint("uq_profile_friend_code", type_="unique")
        batch.drop_column("friend_code")
        for name in SHARES:
            batch.drop_column(name)
