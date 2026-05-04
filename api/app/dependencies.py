from __future__ import annotations

from fastapi import Cookie, Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt import InvalidTokenError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User, Workspace, WorkspaceMember
from app.db.session import get_db
from app.services.auth import decode_access_token
from app.services.workspaces import ensure_personal_workspace

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        user_id = int(payload["sub"])
    except (InvalidTokenError, KeyError, ValueError):
        raise credentials_exception

    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise credentials_exception
    return user


async def get_current_workspace(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    space_header: int | None = Header(default=None, alias="X-Space-Id"),
    workspace_header: int | None = Header(default=None, alias="X-Workspace-Id"),
    space_cookie: int | None = Cookie(default=None, alias="space_id"),
    workspace_cookie: int | None = Cookie(default=None, alias="workspace_id"),
) -> Workspace:
    requested_workspace_id = space_header or workspace_header or space_cookie or workspace_cookie

    if requested_workspace_id is not None:
        stmt = (
            select(Workspace)
            .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
            .where(
                Workspace.id == requested_workspace_id,
                WorkspaceMember.user_id == current_user.id,
            )
            .limit(1)
        )
        workspace = await db.scalar(stmt)
        if workspace is None:
            raise HTTPException(status_code=404, detail="Workspace not found")
        return workspace

    workspace = await ensure_personal_workspace(db, current_user)
    await db.commit()
    await db.refresh(workspace)
    return workspace


async def require_workspace_role(
    allowed_roles: set[str],
    *,
    current_user: User,
    current_workspace: Workspace,
    db: AsyncSession,
) -> WorkspaceMember:
    member = await db.scalar(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == current_workspace.id,
            WorkspaceMember.user_id == current_user.id,
        )
    )
    if member is None or member.role not in allowed_roles:
        raise HTTPException(status_code=403, detail="Insufficient workspace permissions")
    return member


async def get_current_workspace_member(
    current_user: User = Depends(get_current_user),
    current_workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
) -> WorkspaceMember:
    return await require_workspace_role(
        {"owner", "admin", "member"},
        current_user=current_user,
        current_workspace=current_workspace,
        db=db,
    )
