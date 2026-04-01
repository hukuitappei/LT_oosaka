from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException


@pytest.mark.asyncio
async def test_list_learning_items_passes_filters_to_service(monkeypatch):
    from app.routers import learning_items as routes

    db = SimpleNamespace()
    current_user = SimpleNamespace(id=7)
    current_workspace = SimpleNamespace(id=3)
    items = [SimpleNamespace(id=1)]

    monkeypatch.setattr(routes, "require_workspace_role", AsyncMock())
    monkeypatch.setattr(routes, "list_workspace_learning_items", AsyncMock(return_value=items))

    result = await routes.list_learning_items(
        q="validation",
        repository_id=5,
        pr_id=9,
        category="design",
        status="new",
        visibility="workspace_shared",
        limit=25,
        offset=10,
        db=db,
        current_user=current_user,
        current_workspace=current_workspace,
    )

    assert result == items
    routes.list_workspace_learning_items.assert_awaited_once_with(
        db,
        3,
        q="validation",
        repository_id=5,
        pr_id=9,
        category="design",
        status="new",
        visibility="workspace_shared",
        limit=25,
        offset=10,
    )


@pytest.mark.asyncio
async def test_get_learning_item_returns_404_when_missing(monkeypatch):
    from app.routers import learning_items as routes

    db = SimpleNamespace()
    current_user = SimpleNamespace(id=7)
    current_workspace = SimpleNamespace(id=3)

    monkeypatch.setattr(routes, "require_workspace_role", AsyncMock())
    monkeypatch.setattr(
        routes,
        "get_workspace_learning_item",
        AsyncMock(side_effect=routes.LearningItemNotFoundError),
    )

    with pytest.raises(HTTPException) as exc:
        await routes.get_learning_item(
            11,
            db=db,
            current_user=current_user,
            current_workspace=current_workspace,
        )

    assert exc.value.status_code == 404
    routes.get_workspace_learning_item.assert_awaited_once_with(db, 11, 3)


@pytest.mark.asyncio
async def test_get_learning_items_summary_clamps_weeks(monkeypatch):
    from app.routers import learning_items as routes

    db = SimpleNamespace()
    current_user = SimpleNamespace(id=7)
    current_workspace = SimpleNamespace(id=3)
    summary = SimpleNamespace(total_learning_items=0)

    monkeypatch.setattr(routes, "require_workspace_role", AsyncMock())
    monkeypatch.setattr(routes, "summarize_workspace_learning_items", AsyncMock(return_value=summary))

    result = await routes.get_learning_items_summary(
        weeks=99,
        db=db,
        current_user=current_user,
        current_workspace=current_workspace,
    )

    assert result == summary
    routes.summarize_workspace_learning_items.assert_awaited_once_with(db, 3, weeks=26)


@pytest.mark.asyncio
async def test_update_learning_item_returns_400_when_body_empty(monkeypatch):
    from app.routers import learning_items as routes
    from app.schemas.learning_items import LearningItemUpdateRequest

    db = SimpleNamespace()
    current_user = SimpleNamespace(id=7)
    current_workspace = SimpleNamespace(id=3)

    monkeypatch.setattr(routes, "require_workspace_role", AsyncMock())

    with pytest.raises(HTTPException) as exc:
        await routes.update_learning_item(
            11,
            LearningItemUpdateRequest(),
            db=db,
            current_user=current_user,
            current_workspace=current_workspace,
        )

    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_update_learning_item_passes_updates_to_service(monkeypatch):
    from app.routers import learning_items as routes
    from app.schemas.learning_items import LearningItemUpdateRequest

    db = SimpleNamespace()
    current_user = SimpleNamespace(id=7)
    current_workspace = SimpleNamespace(id=3)
    item = SimpleNamespace(id=11, status="applied")

    monkeypatch.setattr(routes, "require_workspace_role", AsyncMock())
    monkeypatch.setattr(routes, "update_workspace_learning_item", AsyncMock(return_value=item))

    result = await routes.update_learning_item(
        11,
        LearningItemUpdateRequest(status="applied"),
        db=db,
        current_user=current_user,
        current_workspace=current_workspace,
    )

    assert result == item
    routes.update_workspace_learning_item.assert_awaited_once_with(
        db,
        11,
        3,
        status="applied",
        visibility=None,
    )
