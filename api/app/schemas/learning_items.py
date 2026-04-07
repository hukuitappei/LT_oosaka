from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

LearningItemStatus = Literal["new", "in_progress", "applied", "ignored"]


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
    status: LearningItemStatus
    visibility: str
    created_at: datetime
    repository: RepositoryRef
    pull_request: PullRequestRef

    model_config = {"from_attributes": True}


class LearningItemsWeeklyPoint(BaseModel):
    year: int
    week: int
    label: str
    learning_count: int


class LearningItemsReusePoint(BaseModel):
    year: int
    week: int
    label: str
    reuse_count: int


class LearningItemsCategoryCount(BaseModel):
    category: str
    count: int


class LearningItemsStatusCount(BaseModel):
    status: LearningItemStatus
    count: int


class LearningItemsSummaryResponse(BaseModel):
    total_learning_items: int
    current_week_count: int
    total_reuse_events: int
    reused_learning_items_count: int
    current_week_reuse_count: int
    weekly_points: list[LearningItemsWeeklyPoint]
    reuse_weekly_points: list[LearningItemsReusePoint]
    top_categories: list[LearningItemsCategoryCount]
    status_counts: list[LearningItemsStatusCount]


class LearningItemUpdateRequest(BaseModel):
    status: LearningItemStatus | None = None
    visibility: str | None = None
