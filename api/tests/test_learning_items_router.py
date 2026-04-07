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

    monkeypatch.setattr(routes, "list_workspace_learning_items", AsyncMock(return_value=items))

    result = await routes.list_learning_items(
        category="design",
        visibility="workspace_shared",
        db=db,
        current_user=current_user,
        current_workspace=current_workspace,
    )

    assert result == items
    routes.list_workspace_learning_items.assert_awaited_once_with(
        db,
        3,
        category="design",
        visibility="workspace_shared",
    )


@pytest.mark.asyncio
async def test_get_learning_item_returns_404_when_missing(monkeypatch):
    from app.routers import learning_items as routes

    db = SimpleNamespace()
    current_user = SimpleNamespace(id=7)
    current_workspace = SimpleNamespace(id=3)

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

    monkeypatch.setattr(routes, "summarize_workspace_learning_items", AsyncMock(return_value=summary))

    result = await routes.get_learning_items_summary(
        weeks=99,
        db=db,
        current_user=current_user,
        current_workspace=current_workspace,
    )

    assert result == summary
    routes.summarize_workspace_learning_items.assert_awaited_once_with(db, 3, weeks=26)
