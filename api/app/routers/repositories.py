from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import PullRequest, Repository, Workspace, User
from app.db.session import get_db
from app.dependencies import get_current_user, get_current_workspace, require_workspace_role

router = APIRouter(prefix="/repositories", tags=["repositories"])


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


@router.get("/", response_model=list[RepositoryResponse])
async def list_repositories(
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
    result = await db.execute(
        select(Repository)
        .where(Repository.workspace_id == current_workspace.id)
        .order_by(Repository.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{repo_id}/pull-requests", response_model=list[PullRequestResponse])
async def list_pull_requests(
    repo_id: int,
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
    repo = await db.scalar(
        select(Repository).where(
            Repository.id == repo_id,
            Repository.workspace_id == current_workspace.id,
        )
    )
    if repo is None:
        raise HTTPException(status_code=404, detail="Repository not found")
    result = await db.execute(
        select(PullRequest)
        .where(PullRequest.repository_id == repo_id)
        .order_by(PullRequest.created_at.desc())
    )
    return result.scalars().all()
