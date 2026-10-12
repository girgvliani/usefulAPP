"""books: unlocked or gifted books, and what their trackers log

Revision ID: 0018
Revises: 0017
Create Date: 2026-10-12

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0018"
down_revision: Union[str, None] = "0017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_books",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("book_key", sa.String(30), nullable=False),
        sa.Column("via", sa.String(10), nullable=False),
        sa.Column("gifted_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("unlocked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("chapters_read", sa.JSON(), nullable=False),
        sa.UniqueConstraint("user_id", "book_key", name="uq_user_book"),
    )
    op.create_index("ix_user_books_user_id", "user_books", ["user_id"])
    op.create_index("ix_user_books_gifted_by", "user_books", ["gifted_by"])
    op.create_table(
        "book_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("book_key", sa.String(30), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_book_entries_user_id", "book_entries", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_book_entries_user_id", table_name="book_entries")
    op.drop_table("book_entries")
    op.drop_index("ix_user_books_gifted_by", table_name="user_books")
    op.drop_index("ix_user_books_user_id", table_name="user_books")
    op.drop_table("user_books")
