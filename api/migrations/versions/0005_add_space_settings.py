"""add space settings

Revision ID: 0005
Revises: 0004
Create Date: 2026-04-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "space_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("workspace_id", sa.Integer(), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("default_visibility", sa.String(length=32), nullable=False, server_default="workspace_shared"),
        sa.Column("active_goal", sa.Text(), nullable=True),
        sa.Column("active_focus_labels", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("primary_repository_ids", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_space_settings_workspace_id"), "space_settings", ["workspace_id"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_space_settings_workspace_id"), table_name="space_settings")
    op.drop_table("space_settings")
