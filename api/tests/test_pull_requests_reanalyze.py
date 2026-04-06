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

    monkeypatch.setattr(routes, "require_workspace_role", AsyncMock())
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

    monkeypatch.setattr(routes, "require_workspace_role", AsyncMock())
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


@pytest.mark.asyncio
async def test_get_pull_request_includes_related_learning_items(monkeypatch):
    from app.routers import pull_requests as routes

    current_user = SimpleNamespace(id=7)
    current_workspace = SimpleNamespace(id=3)
    db = SimpleNamespace()
    pr = SimpleNamespace(
        id=42,
        github_pr_number=42,
        title="Tighten validation",
        state="merged",
        author="alice",
        github_url="https://example.com/pr/42",
        processed=True,
        created_at="2026-03-27T00:00:00",
        learning_items=[],
    )
    related_item = SimpleNamespace(
        id=1,
        title="Validate before persistence",
        detail="detail",
        category="design",
        confidence=0.9,
        action_for_next_time="act",
        evidence="evidence",
        status="applied",
        visibility="workspace_shared",
        created_at="2026-03-20T00:00:00",
        pull_request=SimpleNamespace(
            id=30,
            github_pr_number=30,
            title="Older PR",
            github_url="https://example.com/pr/30",
            repository=SimpleNamespace(id=9, full_name="owner/repo", name="repo"),
        ),
    )
    match = SimpleNamespace(
        item=related_item,
        matched_terms=["validation"],
        match_types=["content_match", "review_match"],
        same_repository=True,
        score=8,
        recommendation_reasons=["Same repository context", "Previously marked as applied"],
    )

    monkeypatch.setattr(routes, "require_workspace_role", AsyncMock())
    monkeypatch.setattr(routes, "get_workspace_pull_request", AsyncMock(return_value=pr))
    monkeypatch.setattr(routes, "get_related_learning_items_for_pull_request", AsyncMock(return_value=[match]))

    response = await routes.get_pull_request(
        42,
        db=db,
        current_user=current_user,
        current_workspace=current_workspace,
    )

    assert response["id"] == 42
    assert response["related_learning_items"][0]["matched_terms"] == ["validation"]
    assert response["related_learning_items"][0]["match_types"] == ["content_match", "review_match"]
    assert response["related_learning_items"][0]["same_repository"] is True
    assert response["related_learning_items"][0]["relevance_score"] == 8
    assert response["related_learning_items"][0]["recommendation_reasons"] == [
        "Same repository context",
        "Previously marked as applied",
    ]
