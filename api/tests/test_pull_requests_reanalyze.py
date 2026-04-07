from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException


@pytest.mark.asyncio
async def test_reanalyze_pull_request_enqueues_celery_task(monkeypatch):
    from app.routers import pull_requests as routes

    current_user = SimpleNamespace(id=7)
    current_workspace = SimpleNamespace(id=3)
    db = SimpleNamespace()

    monkeypatch.setattr(
        routes,
        "request_reanalysis_for_pull_request",
        AsyncMock(return_value={"status": "accepted", "pr_id": 42}),
    )

    response = await routes.reanalyze_pull_request(
        42,
        db=db,
        current_user=current_user,
        current_workspace=current_workspace,
    )

    assert response == {"status": "accepted", "pr_id": 42}
    routes.request_reanalysis_for_pull_request.assert_awaited_once_with(db, 42, 3, 7)


@pytest.mark.asyncio
async def test_reanalyze_pull_request_returns_404_when_pr_missing(monkeypatch):
    from app.routers import pull_requests as routes

    current_user = SimpleNamespace(id=7)
    current_workspace = SimpleNamespace(id=3)
    db = SimpleNamespace()

    monkeypatch.setattr(
        routes,
        "request_reanalysis_for_pull_request",
        AsyncMock(side_effect=routes.PullRequestNotFoundError),
    )

    with pytest.raises(HTTPException) as exc:
        await routes.reanalyze_pull_request(
            42,
            db=db,
            current_user=current_user,
            current_workspace=current_workspace,
        )

    assert exc.value.status_code == 404
    routes.request_reanalysis_for_pull_request.assert_awaited_once_with(db, 42, 3, 7)
