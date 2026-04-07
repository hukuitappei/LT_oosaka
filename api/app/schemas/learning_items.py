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
    pull_request_id: int | None
    title: str
    detail: str
    category: str
    confidence: float
    action_for_next_time: str
    evidence: str
    visibility: str
    created_at: datetime
    repository: RepositoryRef | None
    pull_request: PullRequestRef | None

    model_config = {"from_attributes": True}


class LearningItemsWeeklyPoint(BaseModel):
    year: int
    week: int
    label: str
    learning_count: int


class LearningItemsCategoryCount(BaseModel):
    category: str
    count: int


class LearningItemsSummaryResponse(BaseModel):
    total_learning_items: int
    current_week_count: int
    weekly_points: list[LearningItemsWeeklyPoint]
    top_categories: list[LearningItemsCategoryCount]
