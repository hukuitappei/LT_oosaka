from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User, Workspace
from app.db.session import get_db
from app.dependencies import get_current_user, get_current_workspace, require_workspace_role
from app.services.workspaces import (
    WorkspaceMemberAlreadyExistsError,
    WorkspaceMemberNotFoundError,
    WorkspaceNotFoundError,
    WorkspaceUserNotFoundError,
    add_workspace_member_by_email,
    create_workspace,
    get_user_workspace,
    list_user_workspaces,
    update_workspace_member_role,
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


@router.get("/", response_model=list[WorkspaceOut])
async def list_workspaces(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await list_user_workspaces(db, current_user.id)
    return [
        WorkspaceOut(
            id=workspace.id,
            name=workspace.name,
            slug=workspace.slug,
            is_personal=workspace.is_personal,
            role=role,
            created_at=workspace.created_at,
        )
        for workspace, role in result
    ]


@router.post("/", response_model=WorkspaceOut, status_code=status.HTTP_201_CREATED)
async def create_workspace_endpoint(
    request: CreateWorkspaceRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    workspace = await create_workspace(db, name=request.name, owner=current_user)
    await db.commit()
    await db.refresh(workspace)
    return WorkspaceOut(
        id=workspace.id,
        name=workspace.name,
        slug=workspace.slug,
        is_personal=workspace.is_personal,
        role="owner",
        created_at=workspace.created_at,
    )


@router.get("/{workspace_id}", response_model=WorkspaceOut)
async def get_workspace(
    workspace_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        workspace, role = await get_user_workspace(db, workspace_id, current_user.id)
    except WorkspaceNotFoundError:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return WorkspaceOut(
        id=workspace.id,
        name=workspace.name,
        slug=workspace.slug,
        is_personal=workspace.is_personal,
        role=role,
        created_at=workspace.created_at,
    )


@router.post("/{workspace_id}/members", status_code=status.HTTP_201_CREATED)
async def add_workspace_member(
    workspace_id: int,
    request: AddMemberRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    workspace = await db.get(Workspace, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    await require_workspace_role(
        {"owner", "admin"},
        current_user=current_user,
        current_workspace=workspace,
        db=db,
    )
    try:
        await add_workspace_member_by_email(db, workspace_id, request.email, request.role)
    except WorkspaceUserNotFoundError:
        raise HTTPException(status_code=404, detail="User not found")
    except WorkspaceMemberAlreadyExistsError:
        raise HTTPException(status_code=400, detail="User already belongs to workspace")
    return {"status": "added"}


@router.patch("/{workspace_id}/members/{user_id}")
async def update_workspace_member(
    workspace_id: int,
    user_id: int,
    request: UpdateMemberRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    workspace = await db.get(Workspace, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    await require_workspace_role(
        {"owner", "admin"},
        current_user=current_user,
        current_workspace=workspace,
        db=db,
    )
    try:
        await update_workspace_member_role(db, workspace_id, user_id, request.role)
    except WorkspaceMemberNotFoundError:
        raise HTTPException(status_code=404, detail="Workspace member not found")
    return {"status": "updated"}


@router.get("/current/context", response_model=WorkspaceOut)
async def get_current_workspace_context(
    workspace: Workspace = Depends(get_current_workspace),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    member = await require_workspace_role(
        {"owner", "admin", "member"},
        current_user=current_user,
        current_workspace=workspace,
        db=db,
    )
    return WorkspaceOut(
        id=workspace.id,
        name=workspace.name,
        slug=workspace.slug,
        is_personal=workspace.is_personal,
        role=member.role,
        created_at=workspace.created_at,
    )
