from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException


@pytest.mark.asyncio
async def test_list_weekly_digests_returns_service_result(monkeypatch):
    from app.routers import weekly_digests as routes

    db = SimpleNamespace()
    current_user = SimpleNamespace(id=7)
    current_workspace = SimpleNamespace(id=3)
    digests = [SimpleNamespace(id=1), SimpleNamespace(id=2)]

    monkeypatch.setattr(routes, "list_workspace_weekly_digests", AsyncMock(return_value=digests))

    response = await routes.list_weekly_digests(
        db=db,
        current_user=current_user,
        current_workspace=current_workspace,
    )

    assert response == digests
    routes.list_workspace_weekly_digests.assert_awaited_once_with(db, 3)


@pytest.mark.asyncio
async def test_get_weekly_digest_returns_404_when_missing(monkeypatch):
    from app.routers import weekly_digests as routes

    db = SimpleNamespace()
    current_user = SimpleNamespace(id=7)
    current_workspace = SimpleNamespace(id=3)

    monkeypatch.setattr(
        routes,
        "get_workspace_weekly_digest",
        AsyncMock(side_effect=routes.WeeklyDigestNotFoundError),
    )

    with pytest.raises(HTTPException) as exc:
        await routes.get_weekly_digest(
            11,
            db=db,
            current_user=current_user,
            current_workspace=current_workspace,
        )

    assert exc.value.status_code == 404
    routes.get_workspace_weekly_digest.assert_awaited_once_with(db, 11, 3)


@pytest.mark.asyncio
async def test_generate_digest_uses_resolved_period_and_service(monkeypatch):
    from app.routers import weekly_digests as routes

    db = SimpleNamespace()
    current_user = SimpleNamespace(id=7)
    current_workspace = SimpleNamespace(id=3)
    request = SimpleNamespace(year=None, week=None)
    period = SimpleNamespace(year=2026, week=13)
    digest = SimpleNamespace(id=5)

    monkeypatch.setattr(routes, "resolve_weekly_digest_period", lambda year, week: period)
    monkeypatch.setattr(
        routes,
        "generate_workspace_weekly_digest",
        AsyncMock(return_value=digest),
    )

    response = await routes.generate_digest(
        request,
        db=db,
        current_user=current_user,
        current_workspace=current_workspace,
    )

    assert response is digest
    routes.generate_workspace_weekly_digest.assert_awaited_once_with(
        db,
        3,
        year=2026,
        week=13,
    )


@pytest.mark.asyncio
async def test_generate_digest_returns_400_when_provider_missing(monkeypatch):
    from app.routers import weekly_digests as routes

    db = SimpleNamespace()
    current_user = SimpleNamespace(id=7)
    current_workspace = SimpleNamespace(id=3)
    request = SimpleNamespace(year=2026, week=12)

    monkeypatch.setattr(
        routes,
        "generate_workspace_weekly_digest",
        AsyncMock(side_effect=routes.WeeklyDigestProviderUnavailableError("provider missing")),
    )

    with pytest.raises(HTTPException) as exc:
        await routes.generate_digest(
            request,
            db=db,
            current_user=current_user,
            current_workspace=current_workspace,
        )

    assert exc.value.status_code == 400
    assert exc.value.detail == "provider missing"
