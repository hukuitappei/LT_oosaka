from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User, Workspace
from app.db.session import get_db
from app.dependencies import get_current_user, get_current_workspace, require_workspace_role
from app.services.workspaces import (
    WorkspaceDeleteConfirmationError,
    WorkspaceDeletePermissionError,
    WorkspaceMemberAlreadyExistsError,
    WorkspaceMemberNotFoundError,
    WorkspaceNotFoundError,
    WorkspacePermissionError,
    WorkspaceSummary,
    WorkspaceUserNotFoundError,
    add_workspace_member_to_workspace,
    create_workspace_for_user,
    get_current_workspace_summary,
    get_user_workspace_summary,
    list_user_workspace_summaries,
    purge_workspace,
    update_workspace_member_role_in_workspace,
)

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


class WorkspaceOut(BaseModel):
    id: int
    name: str
    slug: str
    is_personal: bool
    role: str
    created_at: datetime


class CreateWorkspaceRequest(BaseModel):
    name: str


class AddMemberRequest(BaseModel):
    email: str
    role: str = "member"


class UpdateMemberRequest(BaseModel):
    role: str


class PurgeWorkspaceResponse(BaseModel):
    status: str
    workspace_id: int
    deleted_learning_items: int
    deleted_review_comments: int
    deleted_pull_requests: int
    deleted_repositories: int
    deleted_weekly_digests: int
    deleted_github_connections: int
    deleted_memberships: int


def _workspace_out(summary: WorkspaceSummary) -> WorkspaceOut:
    return WorkspaceOut(**summary.__dict__)


@router.get("/", response_model=list[WorkspaceOut])
async def list_workspaces(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return [_workspace_out(summary) for summary in await list_user_workspace_summaries(db, current_user.id)]


@router.post("/", response_model=WorkspaceOut, status_code=status.HTTP_201_CREATED)
async def create_workspace_endpoint(
    request: CreateWorkspaceRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return _workspace_out(await create_workspace_for_user(db, name=request.name, owner=current_user))


@router.get("/{workspace_id}", response_model=WorkspaceOut)
async def get_workspace(
    workspace_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        summary = await get_user_workspace_summary(db, workspace_id, current_user.id)
    except WorkspaceNotFoundError:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return _workspace_out(summary)


@router.post("/{workspace_id}/members", status_code=status.HTTP_201_CREATED)
async def add_workspace_member(
    workspace_id: int,
    request: AddMemberRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        await add_workspace_member_to_workspace(
            db,
            workspace_id=workspace_id,
            actor_user_id=current_user.id,
            email=request.email,
            role=request.role,
        )
    except WorkspaceUserNotFoundError:
        raise HTTPException(status_code=404, detail="User not found")
    except WorkspaceMemberAlreadyExistsError:
        raise HTTPException(status_code=400, detail="User already belongs to workspace")
    except WorkspaceNotFoundError:
        raise HTTPException(status_code=404, detail="Workspace not found")
    except WorkspacePermissionError:
        raise HTTPException(status_code=403, detail="Insufficient workspace permissions")
    return {"status": "added"}


@router.patch("/{workspace_id}/members/{user_id}")
async def update_workspace_member(
    workspace_id: int,
    user_id: int,
    request: UpdateMemberRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        await update_workspace_member_role_in_workspace(
            db,
            workspace_id=workspace_id,
            actor_user_id=current_user.id,
            target_user_id=user_id,
            role=request.role,
        )
    except WorkspaceMemberNotFoundError:
        raise HTTPException(status_code=404, detail="Workspace member not found")
    except WorkspaceNotFoundError:
        raise HTTPException(status_code=404, detail="Workspace not found")
    except WorkspacePermissionError:
        raise HTTPException(status_code=403, detail="Insufficient workspace permissions")
    return {"status": "updated"}


@router.get("/current/context", response_model=WorkspaceOut)
async def get_current_workspace_context(
    workspace: Workspace = Depends(get_current_workspace),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await require_workspace_role(
        {"owner", "admin", "member"},
        current_user=current_user,
        current_workspace=workspace,
        db=db,
    )
    return _workspace_out(
        await get_current_workspace_summary(
            db,
            workspace_id=workspace.id,
            user_id=current_user.id,
        )
    )


@router.delete("/{workspace_id}/purge", response_model=PurgeWorkspaceResponse)
async def purge_workspace_endpoint(
    workspace_id: int,
    confirm_slug: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await purge_workspace(
            db,
            workspace_id=workspace_id,
            actor_user_id=current_user.id,
            confirm_slug=confirm_slug,
        )
    except WorkspaceNotFoundError:
        raise HTTPException(status_code=404, detail="Workspace not found")
    except WorkspaceDeleteConfirmationError:
        raise HTTPException(status_code=400, detail="Workspace confirmation did not match")
    except WorkspaceDeletePermissionError:
        raise HTTPException(status_code=403, detail="Insufficient workspace permissions")

    return PurgeWorkspaceResponse(status="deleted", **result.__dict__)
