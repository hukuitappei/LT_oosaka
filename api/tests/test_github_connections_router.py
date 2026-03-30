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
    workspace = SimpleNamespace(id=3)
    created = SimpleNamespace(id=11)

    monkeypatch.setattr(routes, "_resolve_workspace", AsyncMock(return_value=workspace))
    monkeypatch.setattr(routes, "create_token_github_connection", AsyncMock(return_value=created))

    result = await routes.create_token_connection(
        request,
        current_user=current_user,
        current_workspace=current_workspace,
        db=db,
    )

    assert result == created
    routes.create_token_github_connection.assert_awaited_once_with(
        db,
        workspace_id=3,
        user_id=7,
        access_token="secret-token",
        github_account_login="octocat",
        label="primary",
    )


@pytest.mark.asyncio
async def test_delete_connection_maps_not_found_error(monkeypatch):
    from app.routers import github_connections as routes

    db = SimpleNamespace()
    current_user = SimpleNamespace(id=7)
    current_workspace = SimpleNamespace(id=3)

    monkeypatch.setattr(
        routes,
        "get_visible_github_connection",
        AsyncMock(side_effect=routes.GitHubConnectionNotFoundError),
    )
    monkeypatch.setattr(
        routes,
        "delete_visible_github_connection",
        AsyncMock(),
    )

    with pytest.raises(HTTPException) as exc:
        await routes.delete_connection(
            99,
            current_user=current_user,
            current_workspace=current_workspace,
            db=db,
        )

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_workspace_connection_requires_admin_role(monkeypatch):
    from app.routers import github_connections as routes

    db = SimpleNamespace()
    current_user = SimpleNamespace(id=7)
    current_workspace = SimpleNamespace(id=3)
    connection = SimpleNamespace(workspace_id=3)

    monkeypatch.setattr(routes, "get_visible_github_connection", AsyncMock(return_value=connection))
    monkeypatch.setattr(routes, "require_workspace_role", AsyncMock())
    monkeypatch.setattr(routes, "delete_visible_github_connection", AsyncMock())

    result = await routes.delete_connection(
        11,
        current_user=current_user,
        current_workspace=current_workspace,
        db=db,
    )

    assert result == {"status": "deleted"}
    routes.require_workspace_role.assert_awaited_once()
    routes.delete_visible_github_connection.assert_awaited_once_with(
        db,
        connection_id=11,
        workspace_id=3,
        user_id=7,
    )
