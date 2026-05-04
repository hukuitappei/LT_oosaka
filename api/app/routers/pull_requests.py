from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User, Workspace, WorkspaceMember
from app.db.session import get_db
from app.dependencies import get_current_user, get_current_workspace, get_current_workspace_member, require_workspace_role
from app.services.pull_requests import (
    PullRequestNotFoundError,
    RelatedLearningItemNotFoundError,
    get_related_learning_items_for_pull_request,
    get_workspace_pull_request,
    record_learning_reuse_for_pull_request,
    request_reanalysis_for_pull_request,
)

router = APIRouter(prefix="/pull-requests", tags=["pull-requests"])


class LearningItemOut(BaseModel):
    id: int
    title: str
    detail: str
    category: str
    confidence: float
    action_for_next_time: str
    evidence: str
    status: str
    visibility: str
    created_at: datetime

    model_config = {"from_attributes": True}


class PullRequestRefOut(BaseModel):
    id: int
    github_pr_number: int
    title: str
    github_url: str

    model_config = {"from_attributes": True}


class RepositoryRefOut(BaseModel):
    id: int
    full_name: str
    name: str

    model_config = {"from_attributes": True}


class RelatedLearningItemOut(LearningItemOut):
    repository: RepositoryRefOut
    pull_request: PullRequestRefOut
    matched_terms: list[str]
    match_types: list[str]
    same_repository: bool
    relevance_score: int
    recommendation_reasons: list[str]
    reuse_count: int
    reused_in_current_pr: bool


class LearningReuseRecordOut(BaseModel):
    source_learning_item_id: int
    target_pull_request_id: int
    reuse_count: int
    already_recorded: bool


class PullRequestDetail(BaseModel):
    id: int
    github_pr_number: int
    title: str
    state: str
    author: str
    github_url: str
    processed: bool
    created_at: datetime
    learning_items: list[LearningItemOut] = []
    related_learning_items: list[RelatedLearningItemOut] = []

    model_config = {"from_attributes": True}


@router.get("/{pr_id}", response_model=PullRequestDetail)
async def get_pull_request(
    pr_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_workspace: Workspace = Depends(get_current_workspace),
    _member: WorkspaceMember = Depends(get_current_workspace_member),
):
    pr = await get_workspace_pull_request(db, pr_id, current_workspace.id)
    if not pr:
        raise HTTPException(status_code=404, detail="Pull request not found")
    related_items = await get_related_learning_items_for_pull_request(db, pr, current_workspace.id)
    return {
        **PullRequestDetail.model_validate(pr).model_dump(),
        "related_learning_items": [
            {
                **LearningItemOut.model_validate(match.item).model_dump(),
                "repository": RepositoryRefOut.model_validate(match.item.pull_request.repository).model_dump(),
                "pull_request": PullRequestRefOut.model_validate(match.item.pull_request).model_dump(),
                "matched_terms": match.matched_terms,
                "match_types": match.match_types,
                "same_repository": match.same_repository,
                "relevance_score": match.score,
                "recommendation_reasons": match.recommendation_reasons,
                "reuse_count": match.reuse_count,
                "reused_in_current_pr": match.reused_in_current_pr,
            }
            for match in related_items
        ],
    }


@router.post("/{pr_id}/reanalyze")
async def reanalyze_pull_request(
    pr_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_workspace: Workspace = Depends(get_current_workspace),
    _member: WorkspaceMember = Depends(get_current_workspace_member),
):
    try:
        return await request_reanalysis_for_pull_request(
            db,
            pr_id,
            current_workspace.id,
            current_user.id,
        )
    except PullRequestNotFoundError:
        raise HTTPException(status_code=404, detail="Pull request not found")


@router.post("/{pr_id}/related-learning/{item_id}/reuse", response_model=LearningReuseRecordOut)
async def record_related_learning_reuse(
    pr_id: int,
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
    try:
        return await record_learning_reuse_for_pull_request(
            db,
            source_learning_item_id=item_id,
            target_pr_id=pr_id,
            workspace_id=current_workspace.id,
            user_id=current_user.id,
        )
    except PullRequestNotFoundError:
        raise HTTPException(status_code=404, detail="Pull request not found")
    except RelatedLearningItemNotFoundError:
        raise HTTPException(status_code=404, detail="Related learning item not found")
