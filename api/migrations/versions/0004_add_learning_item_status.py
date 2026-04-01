"""add status to learning_items

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "learning_items",
        sa.Column("status", sa.String(length=32), nullable=False, server_default="new"),
    )


def downgrade() -> None:
    op.drop_column("learning_items", "status")
