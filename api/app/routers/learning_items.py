from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import LearningItem, PullRequest, Repository, User, Workspace
from app.db.session import get_db
from app.dependencies import get_current_user, get_current_workspace, require_workspace_role

router = APIRouter(prefix="/learning-items", tags=["learning-items"])


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


def _to_learning_item_response(item: LearningItem) -> LearningItemResponse:
    pull_request = item.pull_request
    repository = pull_request.repository
    return LearningItemResponse(
        id=item.id,
        pull_request_id=item.pull_request_id,
        title=item.title,
        detail=item.detail,
        category=item.category,
        confidence=item.confidence,
        action_for_next_time=item.action_for_next_time,
        evidence=item.evidence,
        visibility=item.visibility,
        created_at=item.created_at,
        repository=RepositoryRef.model_validate(repository),
        pull_request=PullRequestRef.model_validate(pull_request),
    )


@router.get("/", response_model=list[LearningItemResponse])
async def list_learning_items(
    category: str | None = None,
    visibility: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_workspace: Workspace = Depends(get_current_workspace),
):
    await require_workspace_role(
        {"owner", "admin", "member"},
        current_user=current_user,
        current_workspace=current_workspace,
        db=db,
    )
    stmt = (
        select(LearningItem)
        .join(PullRequest, LearningItem.pull_request_id == PullRequest.id)
        .join(Repository, PullRequest.repository_id == Repository.id)
        .options(
            selectinload(LearningItem.pull_request).selectinload(PullRequest.repository)
        )
        .where(LearningItem.workspace_id == current_workspace.id)
        .order_by(LearningItem.created_at.desc())
    )
    if category:
        stmt = stmt.where(LearningItem.category == category)
    if visibility:
        stmt = stmt.where(LearningItem.visibility == visibility)
    result = await db.execute(stmt)
    return [_to_learning_item_response(item) for item in result.scalars().all()]


@router.get("/{item_id}", response_model=LearningItemResponse)
async def get_learning_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_workspace: Workspace = Depends(get_current_workspace),
):
    await require_workspace_role(
        {"owner", "admin", "member"},
        current_user=current_user,
        current_workspace=current_workspace,
        db=db,
    )
    item = await db.scalar(
        select(LearningItem)
        .join(PullRequest, LearningItem.pull_request_id == PullRequest.id)
        .join(Repository, PullRequest.repository_id == Repository.id)
        .options(
            selectinload(LearningItem.pull_request).selectinload(PullRequest.repository)
        )
        .where(
            LearningItem.id == item_id,
            LearningItem.workspace_id == current_workspace.id,
        )
    )
    if not item:
        raise HTTPException(status_code=404, detail="Learning item not found")
    return _to_learning_item_response(item)
