import sys
from pathlib import Path

import pytest
from sqlalchemy import select

API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.services.connection_secrets import decrypt_github_connection_token, encrypt_github_connection_token
from app.db.models import GitHubConnection, User, Workspace, WorkspaceMember


@pytest.mark.asyncio
async def test_list_visible_github_connections_includes_workspace_and_personal(db_session):
    from app.services.github_connections import list_visible_github_connections

    user = User(email="owner@example.com", hashed_password="hashed::pw")
    other_user = User(email="other@example.com", hashed_password="hashed::pw")
    workspace = Workspace(name="Alpha", slug="alpha", is_personal=False)
    other_workspace = Workspace(name="Beta", slug="beta", is_personal=False)
    db_session.add_all([user, other_user, workspace, other_workspace])
    await db_session.flush()

    db_session.add_all(
        [
            GitHubConnection(
                provider_type="token",
                workspace_id=workspace.id,
                user_id=user.id,
                access_token="workspace-token",
                label="workspace",
            ),
            GitHubConnection(
                provider_type="token",
                workspace_id=None,
                user_id=user.id,
                access_token="personal-token",
                label="personal",
            ),
            GitHubConnection(
                provider_type="token",
                workspace_id=other_workspace.id,
                user_id=other_user.id,
                access_token="other-token",
                label="other",
            ),
        ]
    )
    await db_session.commit()

    result = await list_visible_github_connections(
        db_session,
        workspace_id=workspace.id,
        user_id=user.id,
    )

    assert {connection.label for connection in result} == {"workspace", "personal"}


@pytest.mark.asyncio
async def test_link_app_github_connection_reactivates_existing_installation(db_session):
    from app.services.github_connections import link_app_github_connection

    user = User(email="owner@example.com", hashed_password="hashed::pw")
    workspace = Workspace(name="Alpha", slug="alpha", is_personal=False)
    db_session.add_all([user, workspace])
    await db_session.flush()

    existing = GitHubConnection(
        provider_type="app",
        workspace_id=workspace.id,
        user_id=user.id,
        installation_id=42,
        github_account_login="old-login",
        label="old-label",
        is_active=False,
    )
    db_session.add(existing)
    await db_session.commit()

    connection = await link_app_github_connection(
        db_session,
        workspace_id=workspace.id,
        user_id=user.id,
        installation_id=42,
        github_account_login="new-login",
        label="new-label",
    )

    assert connection.id == existing.id
    assert connection.github_account_login == "new-login"
    assert connection.label == "new-label"
    assert connection.is_active is True


@pytest.mark.asyncio
async def test_delete_visible_github_connection_removes_authorized_connection(db_session):
    from app.services.github_connections import delete_visible_github_connection

    user = User(email="owner@example.com", hashed_password="hashed::pw")
    workspace = Workspace(name="Alpha", slug="alpha", is_personal=False)
    db_session.add_all([user, workspace])
    await db_session.flush()
    db_session.add(WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role="owner"))

    connection = GitHubConnection(
        provider_type="token",
        workspace_id=workspace.id,
        user_id=user.id,
        access_token="token",
    )
    db_session.add(connection)
    await db_session.commit()

    await delete_visible_github_connection(
        db_session,
        connection_id=connection.id,
        workspace_id=workspace.id,
        user_id=user.id,
    )

    deleted = await db_session.scalar(select(GitHubConnection).where(GitHubConnection.id == connection.id))
    assert deleted is None


@pytest.mark.asyncio
async def test_delete_visible_github_connection_rejects_non_admin_workspace_member(db_session):
    from app.services.github_connections import (
        GitHubConnectionWorkspaceDeletePermissionError,
        delete_visible_github_connection,
    )

    user = User(email="member@example.com", hashed_password="hashed::pw")
    workspace = Workspace(name="Alpha", slug="alpha", is_personal=False)
    db_session.add_all([user, workspace])
    await db_session.flush()
    db_session.add(WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role="member"))

    connection = GitHubConnection(
        provider_type="token",
        workspace_id=workspace.id,
        user_id=user.id,
        access_token="token",
    )
    db_session.add(connection)
    await db_session.commit()

    with pytest.raises(GitHubConnectionWorkspaceDeletePermissionError):
        await delete_visible_github_connection(
            db_session,
            connection_id=connection.id,
            workspace_id=workspace.id,
            user_id=user.id,
        )


@pytest.mark.asyncio
async def test_create_token_github_connection_for_workspace_context_requires_admin_membership(db_session):
    from app.services.github_connections import (
        GitHubConnectionWorkspacePermissionError,
        create_token_github_connection_for_workspace_context,
    )

    user = User(email="owner@example.com", hashed_password="hashed::pw")
    workspace = Workspace(name="Alpha", slug="alpha", is_personal=False)
    db_session.add_all([user, workspace])
    await db_session.flush()
    db_session.add(WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role="member"))
    await db_session.commit()

    with pytest.raises(GitHubConnectionWorkspacePermissionError):
        await create_token_github_connection_for_workspace_context(
            db_session,
            requested_workspace_id=None,
            current_workspace_id=workspace.id,
            user_id=user.id,
            access_token="secret-token",
            github_account_login="octocat",
            label="primary",
        )


@pytest.mark.asyncio
async def test_create_token_github_connection_for_workspace_context_creates_connection_for_admin(db_session):
    from app.services.github_connections import create_token_github_connection_for_workspace_context

    user = User(email="owner@example.com", hashed_password="hashed::pw")
    workspace = Workspace(name="Alpha", slug="alpha", is_personal=False)
    db_session.add_all([user, workspace])
    await db_session.flush()
    db_session.add(WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role="admin"))
    await db_session.commit()

    connection = await create_token_github_connection_for_workspace_context(
        db_session,
        requested_workspace_id=None,
        current_workspace_id=workspace.id,
        user_id=user.id,
        access_token="secret-token",
        github_account_login="octocat",
        label="primary",
    )

    assert connection.workspace_id == workspace.id
    assert connection.user_id == user.id
    assert connection.access_token != "secret-token"
    assert decrypt_github_connection_token(connection.access_token) == "secret-token"

    stored = await db_session.scalar(select(GitHubConnection).where(GitHubConnection.id == connection.id))
    assert stored is not None
    assert stored.access_token == connection.access_token


@pytest.mark.asyncio
async def test_get_visible_github_connection_access_token_decrypts_stored_token(db_session):
    from app.services.github_connections import get_visible_github_connection_access_token

    user = User(email="owner@example.com", hashed_password="hashed::pw")
    workspace = Workspace(name="Alpha", slug="alpha", is_personal=False)
    db_session.add_all([user, workspace])
    await db_session.flush()
    db_session.add(WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role="member"))
    connection = GitHubConnection(
        provider_type="token",
        workspace_id=workspace.id,
        user_id=user.id,
        access_token=encrypt_github_connection_token("encrypted-token"),
    )
    db_session.add(connection)
    await db_session.commit()

    access_token = await get_visible_github_connection_access_token(
        db_session,
        connection_id=connection.id,
        workspace_id=workspace.id,
        user_id=user.id,
    )

    assert access_token == "encrypted-token"


@pytest.mark.asyncio
async def test_link_app_github_connection_for_workspace_context_resolves_workspace(db_session):
    from app.services.github_connections import (
        GitHubConnectionWorkspacePermissionError,
        link_app_github_connection_for_workspace_context,
    )

    user = User(email="owner@example.com", hashed_password="hashed::pw")
    workspace = Workspace(name="Alpha", slug="alpha", is_personal=False)
    db_session.add_all([user, workspace])
    await db_session.flush()
    db_session.add(WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role="member"))
    await db_session.commit()

    with pytest.raises(GitHubConnectionWorkspacePermissionError):
        await link_app_github_connection_for_workspace_context(
            db_session,
            requested_workspace_id=None,
            current_workspace_id=workspace.id,
            user_id=user.id,
            installation_id=42,
            github_account_login="octocat",
            label="primary",
        )


@pytest.mark.asyncio
async def test_link_app_github_connection_for_workspace_context_resolves_workspace_for_owner(db_session):
    from app.services.github_connections import link_app_github_connection_for_workspace_context

    user = User(email="owner@example.com", hashed_password="hashed::pw")
    workspace = Workspace(name="Alpha", slug="alpha", is_personal=False)
    db_session.add_all([user, workspace])
    await db_session.flush()
    db_session.add(WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role="owner"))
    await db_session.commit()

    connection = await link_app_github_connection_for_workspace_context(
        db_session,
        requested_workspace_id=None,
        current_workspace_id=workspace.id,
        user_id=user.id,
        installation_id=42,
        github_account_login="octocat",
        label="primary",
    )

    assert connection.workspace_id == workspace.id
    assert connection.user_id == user.id
    assert connection.installation_id == 42


@pytest.mark.asyncio
async def test_resolve_github_connection_workspace_uses_current_workspace_when_request_omitted(db_session):
    from app.services.github_connections import resolve_github_connection_workspace

    user = User(email="owner@example.com", hashed_password="hashed::pw")
    workspace = Workspace(name="Alpha", slug="alpha", is_personal=False)
    db_session.add_all([user, workspace])
    await db_session.flush()
    db_session.add(WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role="admin"))
    await db_session.commit()

    resolved = await resolve_github_connection_workspace(
        db_session,
        requested_workspace_id=None,
        current_workspace_id=workspace.id,
        user_id=user.id,
    )

    assert resolved.id == workspace.id


@pytest.mark.asyncio
async def test_resolve_github_connection_workspace_rejects_user_without_membership(db_session):
    from app.services.github_connections import (
        GitHubConnectionWorkspacePermissionError,
        resolve_github_connection_workspace,
    )

    user = User(email="owner@example.com", hashed_password="hashed::pw")
    workspace = Workspace(name="Alpha", slug="alpha", is_personal=False)
    db_session.add_all([user, workspace])
    await db_session.commit()

    with pytest.raises(GitHubConnectionWorkspacePermissionError):
        await resolve_github_connection_workspace(
            db_session,
            requested_workspace_id=workspace.id,
            current_workspace_id=workspace.id,
            user_id=user.id,
        )
