from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import GitHubConnection, User, Workspace
from app.db.session import get_db
from app.dependencies import get_current_user, get_current_workspace, require_workspace_role

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


async def _resolve_workspace(
    workspace_id: int | None,
    current_workspace: Workspace,
    current_user: User,
    db: AsyncSession,
) -> Workspace:
    workspace = current_workspace if workspace_id is None else await db.get(Workspace, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    await require_workspace_role(
        {"owner", "admin", "member"},
        current_user=current_user,
        current_workspace=workspace,
        db=db,
    )
    return workspace


@router.get("/", response_model=list[GitHubConnectionOut])
async def list_connections(
    current_user: User = Depends(get_current_user),
    current_workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(GitHubConnection).where(
            (GitHubConnection.workspace_id == current_workspace.id)
            | (
                (GitHubConnection.user_id == current_user.id)
                & GitHubConnection.workspace_id.is_(None)
            )
        )
    )
    return result.scalars().all()


@router.post("/token", response_model=GitHubConnectionOut, status_code=status.HTTP_201_CREATED)
async def create_token_connection(
    request: TokenConnectionRequest,
    current_user: User = Depends(get_current_user),
    current_workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    workspace = await _resolve_workspace(request.workspace_id, current_workspace, current_user, db)
    connection = GitHubConnection(
        provider_type="token",
        workspace_id=workspace.id,
        user_id=current_user.id,
        access_token=request.access_token,
        github_account_login=request.github_account_login,
        label=request.label,
    )
    db.add(connection)
    await db.commit()
    await db.refresh(connection)
    return connection


@router.post("/app/link", response_model=GitHubConnectionOut, status_code=status.HTTP_201_CREATED)
async def link_app_connection(
    request: AppConnectionRequest,
    current_user: User = Depends(get_current_user),
    current_workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    workspace = await _resolve_workspace(request.workspace_id, current_workspace, current_user, db)
    existing = await db.scalar(
        select(GitHubConnection).where(
            GitHubConnection.provider_type == "app",
            GitHubConnection.installation_id == request.installation_id,
            GitHubConnection.workspace_id == workspace.id,
        )
    )
    if existing:
        existing.github_account_login = request.github_account_login
        existing.label = request.label
        existing.is_active = True
        connection = existing
    else:
        connection = GitHubConnection(
            provider_type="app",
            workspace_id=workspace.id,
            user_id=current_user.id,
            installation_id=request.installation_id,
            github_account_login=request.github_account_login,
            label=request.label,
        )
        db.add(connection)
    await db.commit()
    await db.refresh(connection)
    return connection


@router.delete("/{connection_id}")
async def delete_connection(
    connection_id: int,
    current_user: User = Depends(get_current_user),
    current_workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    connection = await db.get(GitHubConnection, connection_id)
    if connection is None:
        raise HTTPException(status_code=404, detail="Connection not found")
    if connection.workspace_id is not None and connection.workspace_id != current_workspace.id:
        raise HTTPException(status_code=404, detail="Connection not found")
    if connection.workspace_id is None and connection.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Connection not found")
    if connection.workspace_id is not None:
        await require_workspace_role(
            {"owner", "admin"},
            current_user=current_user,
            current_workspace=current_workspace,
            db=db,
        )
    await db.delete(connection)
    await db.commit()
    return {"status": "deleted"}
