from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class GitHubInstallationRef(BaseModel):
    id: int | None = None


class GitHubRepositoryRef(BaseModel):
    id: int | None = None
    full_name: str = ""
    name: str = ""


class GitHubPullRequestRef(BaseModel):
    number: int | None = None
    merged: bool | None = None
    title: str | None = None
    body: str | None = None
    state: str | None = None
    html_url: str | None = None
    changed_files: int | None = None
    additions: int | None = None
    deletions: int | None = None
    user: dict[str, Any] = {}
    merged_at: str | None = None


class WebhookTaskPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    event_type: str = ""
    action: str = ""
    correlation_id: str = ""
    repository: dict[str, Any] = Field(default_factory=dict)
    pull_request: dict[str, Any] = Field(default_factory=dict)
    installation: dict[str, Any] = Field(default_factory=dict)


class ReviewCommentPayload(BaseModel):
    id: str
    author: str
    body: str
    file: str = ""
    line: int | None = None
    diff_hunk: str = ""
    resolved: bool = False


class PullRequestExtractionPayload(BaseModel):
    pr_id: str
    title: str
    description: str = ""
    diff_summary: str = ""
    review_comments: list[ReviewCommentPayload]


class ExtractionRequest(BaseModel):
    workspace_id: int
    pr_id: int
    created_by_user_id: int | None = None
    repo: str
    pr_number: int
    installation_id: int | None = None
    correlation_id: str | None = None
    pr_dict: dict[str, Any]

    model_config = ConfigDict(extra="allow")


class ReanalysisRequest(BaseModel):
    pr_id: int
    workspace_id: int
    user_id: int

    model_config = ConfigDict(extra="allow")


class RetentionCleanupTaskResult(BaseModel):
    status: str
    deleted_pull_requests: int = 0
    deleted_review_comments: int = 0
    detached_learning_items: int = 0
    deleted_expired_learning_items: int = 0
    deleted_weekly_digests: int = 0
    pr_source_cutoff: datetime
    log_metadata_cutoff: datetime
    learning_cutoff: datetime
    digest_cutoff: datetime

    model_config = ConfigDict(extra="allow")
