"""initial schema with users

Revision ID: 0001
Revises:
Create Date: 2026-03-26

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True, index=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "repositories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("github_id", sa.Integer(), nullable=False, unique=True, index=True),
        sa.Column("full_name", sa.String(255), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
    )

    op.create_table(
        "pull_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("repository_id", sa.Integer(), sa.ForeignKey("repositories.id"), nullable=False),
        sa.Column("github_pr_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("state", sa.String(50), nullable=False),
        sa.Column("author", sa.String(255), nullable=False),
        sa.Column("github_url", sa.String(500), nullable=False),
        sa.Column("merged_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("processed", sa.Boolean(), nullable=False, default=False),
    )

    op.create_table(
        "review_comments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("pull_request_id", sa.Integer(), sa.ForeignKey("pull_requests.id"), nullable=False),
        sa.Column("github_comment_id", sa.Integer(), nullable=False, unique=True),
        sa.Column("author", sa.String(255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("file_path", sa.String(500), nullable=True),
        sa.Column("line_number", sa.Integer(), nullable=True),
        sa.Column("diff_hunk", sa.Text(), nullable=True),
        sa.Column("resolved", sa.Boolean(), nullable=False, default=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "learning_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("pull_request_id", sa.Integer(), sa.ForeignKey("pull_requests.id"), nullable=False),
        sa.Column("schema_version", sa.String(10), nullable=False, default="1.0"),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("action_for_next_time", sa.Text(), nullable=False),
        sa.Column("evidence", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "weekly_digests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("week", sa.Integer(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("repeated_issues", sa.JSON(), nullable=False),
        sa.Column("next_time_notes", sa.JSON(), nullable=False),
        sa.Column("pr_count", sa.Integer(), nullable=False, default=0),
        sa.Column("learning_count", sa.Integer(), nullable=False, default=0),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("weekly_digests")
    op.drop_table("learning_items")
    op.drop_table("review_comments")
    op.drop_table("pull_requests")
    op.drop_table("repositories")
    op.drop_table("users")
