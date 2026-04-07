from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User, Workspace, WorkspaceMember
from app.db.session import get_db
from app.dependencies import get_current_user, get_current_workspace, get_current_workspace_member
from app.services.pull_requests import (
    PullRequestNotFoundError,
    get_workspace_pull_request,
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
    return pr


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
