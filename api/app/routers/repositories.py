from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Workspace, User, WorkspaceMember
from app.db.session import get_db
from app.dependencies import get_current_user, get_current_workspace, get_current_workspace_member
from app.schemas.repositories import PullRequestResponse, RepositoryResponse
from app.services.repositories import (
    RepositoryNotFoundError,
    list_workspace_repositories,
    list_workspace_repository_pull_requests,
)

router = APIRouter(prefix="/repositories", tags=["repositories"])


@router.get("/", response_model=list[RepositoryResponse])
async def list_repositories(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_workspace: Workspace = Depends(get_current_workspace),
    _member: WorkspaceMember = Depends(get_current_workspace_member),
):
    return await list_workspace_repositories(db, current_workspace.id)


@router.get("/{repo_id}/pull-requests", response_model=list[PullRequestResponse])
async def list_pull_requests(
    repo_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_workspace: Workspace = Depends(get_current_workspace),
    _member: WorkspaceMember = Depends(get_current_workspace_member),
):
    try:
        return await list_workspace_repository_pull_requests(db, repo_id, current_workspace.id)
    except RepositoryNotFoundError:
        raise HTTPException(status_code=404, detail="Repository not found")
