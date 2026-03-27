from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.schemas.auth import TokenResponse, UserResponse, WorkspaceSummary
from app.services.auth import create_access_token, hash_password, verify_password
from app.services.workspaces import ensure_personal_workspace, list_user_workspaces


class UserAlreadyExistsError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


async def build_token_response(db: AsyncSession, user: User) -> TokenResponse:
    workspace = await ensure_personal_workspace(db, user)
    await db.commit()
    await db.refresh(workspace)
    return TokenResponse(
        access_token=create_access_token(user.id, user.email),
        default_workspace_id=workspace.id,
    )


async def register_user(db: AsyncSession, email: str, password: str) -> TokenResponse:
    existing = await db.scalar(select(User).where(User.email == email))
    if existing:
        raise UserAlreadyExistsError

    user = User(
        email=email,
        hashed_password=hash_password(password),
    )
    db.add(user)
    await db.flush()
    await ensure_personal_workspace(db, user)
    await db.commit()
    await db.refresh(user)
    return await build_token_response(db, user)


async def login_user(db: AsyncSession, email: str, password: str) -> TokenResponse:
    user = await db.scalar(select(User).where(User.email == email))
    if not user or not verify_password(password, user.hashed_password):
        raise InvalidCredentialsError
    return await build_token_response(db, user)


async def load_workspace_summaries(db: AsyncSession, user_id: int) -> list[WorkspaceSummary]:
    workspace_rows = await list_user_workspaces(db, user_id)
    return [
        WorkspaceSummary(
            id=workspace.id,
            name=workspace.name,
            slug=workspace.slug,
            is_personal=workspace.is_personal,
            role=role,
        )
        for workspace, role in workspace_rows
    ]


async def get_user_profile(db: AsyncSession, user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        github_login=user.github_login,
        is_active=user.is_active,
        created_at=user.created_at,
        workspaces=await load_workspace_summaries(db, user.id),
    )
