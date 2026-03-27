from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException


@pytest.mark.asyncio
async def test_reanalyze_pull_request_enqueues_celery_task(monkeypatch):
    from app.routers import pull_requests as routes

    current_user = SimpleNamespace(id=7)
    current_workspace = SimpleNamespace(id=3)
    db = SimpleNamespace()
    pr = SimpleNamespace(id=42)

    monkeypatch.setattr(routes, "require_workspace_role", AsyncMock())
    monkeypatch.setattr(routes, "_get_workspace_pr", AsyncMock(return_value=pr))

    delay_mock = MagicMock()
    monkeypatch.setattr("app.tasks.extract.reanalyze_pr_task.delay", delay_mock)

    response = await routes.reanalyze_pull_request(
        42,
        db=db,
        current_user=current_user,
        current_workspace=current_workspace,
    )

    assert response == {"status": "accepted", "pr_id": 42}
    delay_mock.assert_called_once_with(42, 3, 7)


@pytest.mark.asyncio
async def test_reanalyze_pull_request_returns_404_when_pr_missing(monkeypatch):
    from app.routers import pull_requests as routes

    current_user = SimpleNamespace(id=7)
    current_workspace = SimpleNamespace(id=3)
    db = SimpleNamespace()

    monkeypatch.setattr(routes, "require_workspace_role", AsyncMock())
    monkeypatch.setattr(routes, "_get_workspace_pr", AsyncMock(return_value=None))

    delay_mock = MagicMock()
    monkeypatch.setattr("app.tasks.extract.reanalyze_pr_task.delay", delay_mock)

    with pytest.raises(HTTPException) as exc:
        await routes.reanalyze_pull_request(
            42,
            db=db,
            current_user=current_user,
            current_workspace=current_workspace,
        )

    assert exc.value.status_code == 404
    delay_mock.assert_not_called()
