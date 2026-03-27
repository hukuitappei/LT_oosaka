from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException


@pytest.mark.asyncio
async def test_list_repositories_returns_service_result(monkeypatch):
    from app.routers import repositories as routes

    db = SimpleNamespace()
    current_user = SimpleNamespace(id=7)
    current_workspace = SimpleNamespace(id=3)
    repos = [SimpleNamespace(id=1), SimpleNamespace(id=2)]

    monkeypatch.setattr(routes, "require_workspace_role", AsyncMock())
    monkeypatch.setattr(routes, "list_workspace_repositories", AsyncMock(return_value=repos))

    result = await routes.list_repositories(
        db=db,
        current_user=current_user,
        current_workspace=current_workspace,
    )

    assert result == repos
    routes.list_workspace_repositories.assert_awaited_once_with(db, 3)


@pytest.mark.asyncio
async def test_list_pull_requests_returns_404_when_repo_missing(monkeypatch):
    from app.routers import repositories as routes

    db = SimpleNamespace()
    current_user = SimpleNamespace(id=7)
    current_workspace = SimpleNamespace(id=3)

    monkeypatch.setattr(routes, "require_workspace_role", AsyncMock())
    monkeypatch.setattr(
        routes,
        "list_workspace_repository_pull_requests",
        AsyncMock(side_effect=routes.RepositoryNotFoundError),
    )

    with pytest.raises(HTTPException) as exc:
        await routes.list_pull_requests(
            99,
            db=db,
            current_user=current_user,
            current_workspace=current_workspace,
        )

    assert exc.value.status_code == 404
    routes.list_workspace_repository_pull_requests.assert_awaited_once_with(db, 99, 3)
