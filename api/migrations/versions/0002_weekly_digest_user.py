"""add user_id to weekly_digests

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-26

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "weekly_digests",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
    )
    op.create_index("ix_weekly_digests_user_id", "weekly_digests", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_weekly_digests_user_id", table_name="weekly_digests")
    op.drop_column("weekly_digests", "user_id")
