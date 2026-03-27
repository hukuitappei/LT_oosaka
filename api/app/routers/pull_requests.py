from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import PullRequest, Repository, User, Workspace
from app.db.session import get_db
from app.dependencies import get_current_user, get_current_workspace, require_workspace_role

router = APIRouter(prefix="/pull-requests", tags=["pull-requests"])


class LearningItemOut(BaseModel):
    id: int
    title: str
    detail: str
    category: str
    confidence: float
    action_for_next_time: str
    evidence: str
    visibility: str
    created_at: datetime

    model_config = {"from_attributes": True}


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

    model_config = {"from_attributes": True}


async def _get_workspace_pr(
    db: AsyncSession,
    pr_id: int,
    workspace_id: int,
) -> PullRequest | None:
    return await db.scalar(
        select(PullRequest)
        .join(Repository, PullRequest.repository_id == Repository.id)
        .options(selectinload(PullRequest.learning_items))
        .where(PullRequest.id == pr_id, Repository.workspace_id == workspace_id)
    )


@router.get("/{pr_id}", response_model=PullRequestDetail)
async def get_pull_request(
    pr_id: int,
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
    pr = await _get_workspace_pr(db, pr_id, current_workspace.id)
    if not pr:
        raise HTTPException(status_code=404, detail="Pull request not found")
    return pr


@router.post("/{pr_id}/reanalyze")
async def reanalyze_pull_request(
    pr_id: int,
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
    pr = await _get_workspace_pr(db, pr_id, current_workspace.id)
    if not pr:
        raise HTTPException(status_code=404, detail="Pull request not found")

    from app.tasks.extract import reanalyze_pr_task

    reanalyze_pr_task.delay(pr_id, current_workspace.id, current_user.id)
    return {"status": "accepted", "pr_id": pr_id}
