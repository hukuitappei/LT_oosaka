from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    github_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, unique=True)
    github_login: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    memberships: Mapped[list["WorkspaceMember"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    github_connections: Mapped[list["GitHubConnection"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    created_learning_items: Mapped[list["LearningItem"]] = relationship(
        back_populates="created_by_user",
        foreign_keys="LearningItem.created_by_user_id",
    )


class Workspace(Base):
    __tablename__ = "workspaces"
    __table_args__ = (UniqueConstraint("slug", name="uq_workspace_slug"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(255), index=True)
    is_personal: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    memberships: Mapped[list["WorkspaceMember"]] = relationship(
        back_populates="workspace",
        cascade="all, delete-orphan",
    )
    repositories: Mapped[list["Repository"]] = relationship(back_populates="workspace")
    weekly_digests: Mapped[list["WeeklyDigest"]] = relationship(back_populates="workspace")
    learning_items: Mapped[list["LearningItem"]] = relationship(back_populates="workspace")
    github_connections: Mapped[list["GitHubConnection"]] = relationship(back_populates="workspace")


class WorkspaceMember(Base):
    __tablename__ = "workspace_members"
    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", name="uq_workspace_member"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    role: Mapped[str] = mapped_column(String(32), default="member")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    workspace: Mapped["Workspace"] = relationship(back_populates="memberships")
    user: Mapped["User"] = relationship(back_populates="memberships")


class GitHubConnection(Base):
    __tablename__ = "github_connections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider_type: Mapped[str] = mapped_column(String(32))
    workspace_id: Mapped[int | None] = mapped_column(ForeignKey("workspaces.id"), nullable=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    installation_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    github_account_login: Mapped[str | None] = mapped_column(String(255), nullable=True)
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    workspace: Mapped["Workspace | None"] = relationship(back_populates="github_connections")
    user: Mapped["User | None"] = relationship(back_populates="github_connections")
    repositories: Mapped[list["Repository"]] = relationship(back_populates="github_connection")


class Repository(Base):
    __tablename__ = "repositories"
    __table_args__ = (
        UniqueConstraint("workspace_id", "github_id", name="uq_repo_workspace_github"),
        UniqueConstraint("workspace_id", "full_name", name="uq_repo_workspace_full_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    github_connection_id: Mapped[int | None] = mapped_column(
        ForeignKey("github_connections.id"),
        nullable=True,
    )
    github_id: Mapped[int] = mapped_column(Integer, index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    workspace: Mapped["Workspace"] = relationship(back_populates="repositories")
    github_connection: Mapped["GitHubConnection | None"] = relationship(back_populates="repositories")
    pull_requests: Mapped[list["PullRequest"]] = relationship(back_populates="repository")


class PullRequest(Base):
    __tablename__ = "pull_requests"
    __table_args__ = (
        UniqueConstraint("repository_id", "github_pr_number", name="uq_repo_pr_number"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    repository_id: Mapped[int] = mapped_column(ForeignKey("repositories.id"))
    github_pr_number: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(500))
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    state: Mapped[str] = mapped_column(String(50))
    author: Mapped[str] = mapped_column(String(255))
    github_url: Mapped[str] = mapped_column(String(500))
    merged_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    processed: Mapped[bool] = mapped_column(Boolean, default=False)

    repository: Mapped["Repository"] = relationship(back_populates="pull_requests")
    review_comments: Mapped[list["ReviewComment"]] = relationship(back_populates="pull_request")
    learning_items: Mapped[list["LearningItem"]] = relationship(back_populates="pull_request")


class ReviewComment(Base):
    __tablename__ = "review_comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pull_request_id: Mapped[int] = mapped_column(ForeignKey("pull_requests.id"))
    github_comment_id: Mapped[int] = mapped_column(Integer, unique=True)
    author: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    line_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    diff_hunk: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    pull_request: Mapped["PullRequest"] = relationship(back_populates="review_comments")


class LearningItem(Base):
    __tablename__ = "learning_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    pull_request_id: Mapped[int | None] = mapped_column(ForeignKey("pull_requests.id"), nullable=True)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    source_repository_full_name: Mapped[str] = mapped_column(String(255), default="")
    source_repository_name: Mapped[str] = mapped_column(String(255), default="")
    source_github_pr_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_pr_title: Mapped[str] = mapped_column(String(500), default="")
    source_pr_github_url: Mapped[str] = mapped_column(String(500), default="")
    visibility: Mapped[str] = mapped_column(String(32), default="private_draft")
    schema_version: Mapped[str] = mapped_column(String(10), default="1.0")
    title: Mapped[str] = mapped_column(String(255))
    detail: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(100))
    confidence: Mapped[float] = mapped_column(Float)
    action_for_next_time: Mapped[str] = mapped_column(Text)
    evidence: Mapped[str] = mapped_column(Text)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    workspace: Mapped["Workspace"] = relationship(back_populates="learning_items")
    pull_request: Mapped["PullRequest | None"] = relationship(back_populates="learning_items")
    created_by_user: Mapped["User | None"] = relationship(
        back_populates="created_learning_items",
        foreign_keys=[created_by_user_id],
    )


class WeeklyDigest(Base):
    __tablename__ = "weekly_digests"
    __table_args__ = (
        UniqueConstraint("workspace_id", "year", "week", name="uq_workspace_digest_week"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    visibility: Mapped[str] = mapped_column(String(32), default="workspace_shared")
    year: Mapped[int] = mapped_column(Integer)
    week: Mapped[int] = mapped_column(Integer)
    summary: Mapped[str] = mapped_column(Text)
    repeated_issues: Mapped[list] = mapped_column(JSON, default=list)
    next_time_notes: Mapped[list] = mapped_column(JSON, default=list)
    pr_count: Mapped[int] = mapped_column(Integer, default=0)
    learning_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    workspace: Mapped["Workspace"] = relationship(back_populates="weekly_digests")
