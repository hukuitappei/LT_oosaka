from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User, Workspace
from app.db.session import get_db
from app.dependencies import get_current_user, get_current_workspace
from app.services.github_connections import (
    GitHubConnectionNotFoundError,
    GitHubConnectionWorkspaceDeletePermissionError,
    GitHubConnectionWorkspaceNotFoundError,
    GitHubConnectionWorkspacePermissionError,
    create_token_github_connection_for_workspace_context,
    delete_visible_github_connection,
    link_app_github_connection_for_workspace_context,
    list_visible_github_connections,
)

router = APIRouter(prefix="/github-connections", tags=["github-connections"])


class GitHubConnectionOut(BaseModel):
    id: int
    provider_type: str
    workspace_id: int | None
    user_id: int | None
    installation_id: int | None
    github_account_login: str | None
    label: str | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenConnectionRequest(BaseModel):
    access_token: str
    github_account_login: str | None = None
    label: str | None = None
    workspace_id: int | None = None


class AppConnectionRequest(BaseModel):
    installation_id: int
    github_account_login: str | None = None
    label: str | None = None
    workspace_id: int | None = None


@router.get("/", response_model=list[GitHubConnectionOut])
async def list_connections(
    current_user: User = Depends(get_current_user),
    current_workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    return await list_visible_github_connections(
        db,
        workspace_id=current_workspace.id,
        user_id=current_user.id,
    )


@router.post("/token", response_model=GitHubConnectionOut, status_code=status.HTTP_201_CREATED)
async def create_token_connection(
    request: TokenConnectionRequest,
    current_user: User = Depends(get_current_user),
    current_workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await create_token_github_connection_for_workspace_context(
            db,
            requested_workspace_id=request.workspace_id,
            current_workspace_id=current_workspace.id,
            user_id=current_user.id,
            access_token=request.access_token,
            github_account_login=request.github_account_login,
            label=request.label,
        )
    except GitHubConnectionWorkspaceNotFoundError:
        raise HTTPException(status_code=404, detail="Workspace not found")
    except GitHubConnectionWorkspacePermissionError:
        raise HTTPException(status_code=403, detail="Insufficient workspace permissions")


@router.post("/app/link", response_model=GitHubConnectionOut, status_code=status.HTTP_201_CREATED)
async def link_app_connection(
    request: AppConnectionRequest,
    current_user: User = Depends(get_current_user),
    current_workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await link_app_github_connection_for_workspace_context(
            db,
            requested_workspace_id=request.workspace_id,
            current_workspace_id=current_workspace.id,
            user_id=current_user.id,
            installation_id=request.installation_id,
            github_account_login=request.github_account_login,
            label=request.label,
        )
    except GitHubConnectionWorkspaceNotFoundError:
        raise HTTPException(status_code=404, detail="Workspace not found")
    except GitHubConnectionWorkspacePermissionError:
        raise HTTPException(status_code=403, detail="Insufficient workspace permissions")


@router.delete("/{connection_id}")
async def delete_connection(
    connection_id: int,
    current_user: User = Depends(get_current_user),
    current_workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    try:
        await delete_visible_github_connection(
            db,
            connection_id=connection_id,
            workspace_id=current_workspace.id,
            user_id=current_user.id,
        )
    except GitHubConnectionNotFoundError:
        raise HTTPException(status_code=404, detail="Connection not found")
    except GitHubConnectionWorkspaceDeletePermissionError:
        raise HTTPException(status_code=403, detail="Insufficient workspace permissions")
    return {"status": "deleted"}
