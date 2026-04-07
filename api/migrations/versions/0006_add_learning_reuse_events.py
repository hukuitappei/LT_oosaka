"""add learning reuse events

Revision ID: 0006
Revises: 0005
Create Date: 2026-04-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "learning_reuse_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("workspace_id", sa.Integer(), nullable=False),
        sa.Column("source_learning_item_id", sa.Integer(), nullable=False),
        sa.Column("target_pull_request_id", sa.Integer(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["source_learning_item_id"], ["learning_items.id"]),
        sa.ForeignKeyConstraint(["target_pull_request_id"], ["pull_requests.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_learning_item_id",
            "target_pull_request_id",
            name="uq_learning_reuse_source_target",
        ),
    )
    op.create_index(op.f("ix_learning_reuse_events_workspace_id"), "learning_reuse_events", ["workspace_id"], unique=False)
    op.create_index(
        op.f("ix_learning_reuse_events_source_learning_item_id"),
        "learning_reuse_events",
        ["source_learning_item_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_learning_reuse_events_target_pull_request_id"),
        "learning_reuse_events",
        ["target_pull_request_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_learning_reuse_events_target_pull_request_id"), table_name="learning_reuse_events")
    op.drop_index(op.f("ix_learning_reuse_events_source_learning_item_id"), table_name="learning_reuse_events")
    op.drop_index(op.f("ix_learning_reuse_events_workspace_id"), table_name="learning_reuse_events")
    op.drop_table("learning_reuse_events")
