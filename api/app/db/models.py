from datetime import datetime
from sqlalchemy import String, Integer, Float, Text, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    repositories: Mapped[list["Repository"]] = relationship(back_populates="owner")


class Repository(Base):
    __tablename__ = "repositories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    github_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    owner: Mapped["User | None"] = relationship(back_populates="repositories")
    pull_requests: Mapped[list["PullRequest"]] = relationship(back_populates="repository")


class PullRequest(Base):
    __tablename__ = "pull_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    repository_id: Mapped[int] = mapped_column(ForeignKey("repositories.id"))
    github_pr_number: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(500))
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    state: Mapped[str] = mapped_column(String(50))  # open / closed / merged
    author: Mapped[str] = mapped_column(String(255))
    github_url: Mapped[str] = mapped_column(String(500))
    merged_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
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
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    pull_request: Mapped["PullRequest"] = relationship(back_populates="review_comments")


class LearningItem(Base):
    __tablename__ = "learning_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pull_request_id: Mapped[int] = mapped_column(ForeignKey("pull_requests.id"))
    schema_version: Mapped[str] = mapped_column(String(10), default="1.0")
    title: Mapped[str] = mapped_column(String(255))
    detail: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(100))
    confidence: Mapped[float] = mapped_column(Float)
    action_for_next_time: Mapped[str] = mapped_column(Text)
    evidence: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    pull_request: Mapped["PullRequest"] = relationship(back_populates="learning_items")


class WeeklyDigest(Base):
    __tablename__ = "weekly_digests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    year: Mapped[int] = mapped_column(Integer)
    week: Mapped[int] = mapped_column(Integer)
    summary: Mapped[str] = mapped_column(Text)
    repeated_issues: Mapped[list] = mapped_column(JSON, default=list)
    next_time_notes: Mapped[list] = mapped_column(JSON, default=list)
    pr_count: Mapped[int] = mapped_column(Integer, default=0)
    learning_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
