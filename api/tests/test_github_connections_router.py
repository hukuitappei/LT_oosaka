from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException


@pytest.mark.asyncio
async def test_list_connections_returns_service_rows(monkeypatch):
    from app.routers import github_connections as routes

    db = SimpleNamespace()
    current_user = SimpleNamespace(id=7)
    current_workspace = SimpleNamespace(id=3)
    connections = [SimpleNamespace(id=1), SimpleNamespace(id=2)]

    monkeypatch.setattr(routes, "list_user_github_connections", AsyncMock(return_value=connections))

    result = await routes.list_connections(
        current_user=current_user,
        current_workspace=current_workspace,
        db=db,
    )

    assert result == connections
    routes.list_user_github_connections.assert_awaited_once_with(
        db,
        current_user_id=7,
        current_workspace_id=3,
    )


@pytest.mark.asyncio
async def test_create_token_connection_resolves_workspace_and_calls_service(monkeypatch):
    from app.routers import github_connections as routes

    db = SimpleNamespace()
    current_user = SimpleNamespace(id=7)
    current_workspace = SimpleNamespace(id=3)
    workspace = SimpleNamespace(id=9)
    connection = SimpleNamespace(id=1)
    request = routes.TokenConnectionRequest(access_token="secret", github_account_login="octocat", label="main")

    monkeypatch.setattr(routes, "resolve_workspace_for_connection", AsyncMock(return_value=workspace))
    monkeypatch.setattr(routes, "require_workspace_role", AsyncMock())
    monkeypatch.setattr(routes, "create_token_github_connection", AsyncMock(return_value=connection))

    result = await routes.create_token_connection(
        request,
        current_user=current_user,
        current_workspace=current_workspace,
        db=db,
    )

    assert result == connection
    routes.create_token_github_connection.assert_awaited_once_with(
        db,
        workspace_id=9,
        user_id=7,
        access_token="secret",
        github_account_login="octocat",
        label="main",
    )


@pytest.mark.asyncio
async def test_delete_connection_maps_missing_service_result_to_404(monkeypatch):
    from app.routers import github_connections as routes

    db = SimpleNamespace(get=AsyncMock(return_value=SimpleNamespace(workspace_id=None, user_id=7)))
    current_user = SimpleNamespace(id=7)
    current_workspace = SimpleNamespace(id=3)

    monkeypatch.setattr(
        routes,
        "delete_accessible_github_connection",
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
