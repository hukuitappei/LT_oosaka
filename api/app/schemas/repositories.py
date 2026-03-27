from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class RepositoryResponse(BaseModel):
    id: int
    github_id: int
    full_name: str
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}


class PullRequestResponse(BaseModel):
    id: int
    github_pr_number: int
    title: str
    state: str
    author: str
    github_url: str
    processed: bool
    merged_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
