import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))


@pytest.mark.asyncio
async def test_list_connections_uses_service(monkeypatch):
    from app.routers import github_connections as routes

    db = SimpleNamespace()
    current_user = SimpleNamespace(id=7)
    current_workspace = SimpleNamespace(id=3)
    expected = [SimpleNamespace(id=1)]

    monkeypatch.setattr(routes, "list_visible_github_connections", AsyncMock(return_value=expected))

    result = await routes.list_connections(
        current_user=current_user,
        current_workspace=current_workspace,
        db=db,
    )

    assert result == expected
    routes.list_visible_github_connections.assert_awaited_once_with(
        db,
        workspace_id=3,
        user_id=7,
    )


@pytest.mark.asyncio
async def test_create_token_connection_uses_service(monkeypatch):
    from app.routers import github_connections as routes

    db = SimpleNamespace()
    current_user = SimpleNamespace(id=7)
    current_workspace = SimpleNamespace(id=3)
    request = routes.TokenConnectionRequest(
        access_token="secret-token",
        github_account_login="octocat",
        label="primary",
        workspace_id=None,
    )
    created = SimpleNamespace(id=11)

    monkeypatch.setattr(
        routes,
        "create_token_github_connection_for_workspace_context",
        AsyncMock(return_value=created),
    )

    result = await routes.create_token_connection(
        request,
        current_user=current_user,
        current_workspace=current_workspace,
        db=db,
    )

    assert result == created
    routes.create_token_github_connection_for_workspace_context.assert_awaited_once_with(
        db,
        requested_workspace_id=None,
        current_workspace_id=3,
        user_id=7,
        access_token="secret-token",
        github_account_login="octocat",
        label="primary",
    )


@pytest.mark.asyncio
async def test_create_token_connection_maps_workspace_permission_error(monkeypatch):
    from app.routers import github_connections as routes

    db = SimpleNamespace()
    current_user = SimpleNamespace(id=7)
    current_workspace = SimpleNamespace(id=3)
    request = routes.TokenConnectionRequest(access_token="secret-token")

    monkeypatch.setattr(
        routes,
        "create_token_github_connection_for_workspace_context",
        AsyncMock(side_effect=routes.GitHubConnectionWorkspacePermissionError),
    )

    with pytest.raises(HTTPException) as exc:
        await routes.create_token_connection(
            request,
            current_user=current_user,
            current_workspace=current_workspace,
            db=db,
        )

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_delete_connection_uses_service(monkeypatch):
    from app.routers import github_connections as routes

    db = SimpleNamespace()
    current_user = SimpleNamespace(id=7)
    current_workspace = SimpleNamespace(id=3)

    monkeypatch.setattr(
        routes,
        "delete_visible_github_connection",
        AsyncMock(return_value=None),
    )

    result = await routes.delete_connection(
        99,
        current_user=current_user,
        current_workspace=current_workspace,
        db=db,
    )

    assert result == {"status": "deleted"}
    routes.delete_visible_github_connection.assert_awaited_once_with(
        db,
        connection_id=99,
        workspace_id=3,
        user_id=7,
    )


@pytest.mark.asyncio
async def test_delete_connection_maps_not_found_error(monkeypatch):
    from app.routers import github_connections as routes

    db = SimpleNamespace()
    current_user = SimpleNamespace(id=7)
    current_workspace = SimpleNamespace(id=3)

    monkeypatch.setattr(
        routes,
        "delete_visible_github_connection",
        AsyncMock(side_effect=routes.GitHubConnectionNotFoundError),
    )

    with pytest.raises(HTTPException) as exc:
        await routes.delete_connection(
            11,
            current_user=current_user,
            current_workspace=current_workspace,
            db=db,
        )

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_connection_maps_permission_error(monkeypatch):
    from app.routers import github_connections as routes

    db = SimpleNamespace()
    current_user = SimpleNamespace(id=7)
    current_workspace = SimpleNamespace(id=3)

    monkeypatch.setattr(
        routes,
        "delete_visible_github_connection",
        AsyncMock(side_effect=routes.GitHubConnectionWorkspaceDeletePermissionError),
    )

    with pytest.raises(HTTPException) as exc:
        await routes.delete_connection(
            11,
            current_user=current_user,
            current_workspace=current_workspace,
            db=db,
        )

    assert exc.value.status_code == 403
