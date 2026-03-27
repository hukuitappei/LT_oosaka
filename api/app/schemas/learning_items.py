from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class RepositoryRef(BaseModel):
    id: int
    full_name: str
    name: str

    model_config = {"from_attributes": True}


class PullRequestRef(BaseModel):
    id: int
    github_pr_number: int
    title: str
    github_url: str

    model_config = {"from_attributes": True}


class LearningItemResponse(BaseModel):
    id: int
    pull_request_id: int
    title: str
    detail: str
    category: str
    confidence: float
    action_for_next_time: str
    evidence: str
    visibility: str
    created_at: datetime
    repository: RepositoryRef
    pull_request: PullRequestRef

    model_config = {"from_attributes": True}
