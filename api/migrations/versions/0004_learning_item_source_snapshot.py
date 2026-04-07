"""make learning_items independent from pull_requests

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-07

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
        sa.Column("source_repository_full_name", sa.String(length=255), nullable=False, server_default=""),
    )
    op.add_column(
        "learning_items",
        sa.Column("source_repository_name", sa.String(length=255), nullable=False, server_default=""),
    )
    op.add_column(
        "learning_items",
        sa.Column("source_github_pr_number", sa.Integer(), nullable=True),
    )
    op.add_column(
        "learning_items",
        sa.Column("source_pr_title", sa.String(length=500), nullable=False, server_default=""),
    )
    op.add_column(
        "learning_items",
        sa.Column("source_pr_github_url", sa.String(length=500), nullable=False, server_default=""),
    )
    op.execute(
        """
        UPDATE learning_items
        SET
            source_repository_full_name = repositories.full_name,
            source_repository_name = repositories.name,
            source_github_pr_number = pull_requests.github_pr_number,
            source_pr_title = pull_requests.title,
            source_pr_github_url = pull_requests.github_url
        FROM pull_requests
        JOIN repositories ON repositories.id = pull_requests.repository_id
        WHERE learning_items.pull_request_id = pull_requests.id
        """
    )
    op.alter_column("learning_items", "pull_request_id", existing_type=sa.Integer(), nullable=True)
    op.alter_column("learning_items", "source_repository_full_name", server_default=None)
    op.alter_column("learning_items", "source_repository_name", server_default=None)
    op.alter_column("learning_items", "source_pr_title", server_default=None)
    op.alter_column("learning_items", "source_pr_github_url", server_default=None)


def downgrade() -> None:
    op.alter_column("learning_items", "pull_request_id", existing_type=sa.Integer(), nullable=False)
    op.drop_column("learning_items", "source_pr_github_url")
    op.drop_column("learning_items", "source_pr_title")
    op.drop_column("learning_items", "source_github_pr_number")
    op.drop_column("learning_items", "source_repository_name")
    op.drop_column("learning_items", "source_repository_full_name")
