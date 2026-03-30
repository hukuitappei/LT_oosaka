from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import GitHubConnection


class GitHubConnectionNotFoundError(Exception):
    pass


async def get_visible_github_connection(
    db: AsyncSession,
    *,
    connection_id: int,
    workspace_id: int,
    user_id: int,
) -> GitHubConnection:
    connection = await db.get(GitHubConnection, connection_id)
    if connection is None:
        raise GitHubConnectionNotFoundError
    if connection.workspace_id is not None and connection.workspace_id != workspace_id:
        raise GitHubConnectionNotFoundError
    if connection.workspace_id is None and connection.user_id != user_id:
        raise GitHubConnectionNotFoundError
    return connection


async def list_visible_github_connections(
    db: AsyncSession,
    *,
    workspace_id: int,
    user_id: int,
) -> list[GitHubConnection]:
    result = await db.execute(
        select(GitHubConnection).where(
            (GitHubConnection.workspace_id == workspace_id)
            | (
                (GitHubConnection.user_id == user_id)
                & GitHubConnection.workspace_id.is_(None)
            )
        )
    )
    return result.scalars().all()


async def create_token_github_connection(
    db: AsyncSession,
    *,
    workspace_id: int,
    user_id: int,
    access_token: str,
    github_account_login: str | None = None,
    label: str | None = None,
) -> GitHubConnection:
    connection = GitHubConnection(
        provider_type="token",
        workspace_id=workspace_id,
        user_id=user_id,
        access_token=access_token,
        github_account_login=github_account_login,
        label=label,
    )
    db.add(connection)
    await db.commit()
    await db.refresh(connection)
    return connection


async def link_app_github_connection(
    db: AsyncSession,
    *,
    workspace_id: int,
    user_id: int,
    installation_id: int,
    github_account_login: str | None = None,
    label: str | None = None,
) -> GitHubConnection:
    existing = await db.scalar(
        select(GitHubConnection).where(
            GitHubConnection.provider_type == "app",
            GitHubConnection.installation_id == installation_id,
            GitHubConnection.workspace_id == workspace_id,
        )
    )
    if existing:
        existing.github_account_login = github_account_login
        existing.label = label
        existing.is_active = True
        connection = existing
    else:
        connection = GitHubConnection(
            provider_type="app",
            workspace_id=workspace_id,
            user_id=user_id,
            installation_id=installation_id,
            github_account_login=github_account_login,
            label=label,
        )
        db.add(connection)
    await db.commit()
    await db.refresh(connection)
    return connection


async def delete_visible_github_connection(
    db: AsyncSession,
    *,
    connection_id: int,
    workspace_id: int,
    user_id: int,
) -> None:
    connection = await get_visible_github_connection(
        db,
        connection_id=connection_id,
        workspace_id=workspace_id,
        user_id=user_id,
    )
    await db.delete(connection)
    await db.commit()
