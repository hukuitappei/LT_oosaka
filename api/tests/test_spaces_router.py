from datetime import datetime
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
async def test_list_spaces_returns_workspace_rows(monkeypatch):
    from app.routers import spaces as routes

    db = SimpleNamespace()
    current_user = SimpleNamespace(id=7)
    workspace = SimpleNamespace(
        id=3,
        name="Alpha",
        slug="alpha",
        is_personal=False,
        created_at=datetime(2026, 3, 27),
    )

    monkeypatch.setattr(routes, "list_user_workspaces", AsyncMock(return_value=[(workspace, "admin")]))

    result = await routes.list_spaces(current_user=current_user, db=db)

    assert len(result) == 1
    assert result[0].id == 3
    assert result[0].role == "admin"


@pytest.mark.asyncio
async def test_get_space_settings_returns_default_view(monkeypatch):
    from app.routers import spaces as routes

    db = SimpleNamespace()
    current_user = SimpleNamespace(id=7)
    workspace = SimpleNamespace(id=3, name="Alpha")

    monkeypatch.setattr(routes, "get_user_workspace", AsyncMock(return_value=(workspace, "owner")))
    monkeypatch.setattr(routes, "require_workspace_role", AsyncMock())
    monkeypatch.setattr(
        routes,
        "get_space_settings_view",
        AsyncMock(
            return_value=SimpleNamespace(
                workspace_id=3,
                display_name="Alpha",
                description=None,
                default_visibility="workspace_shared",
                active_goal=None,
                active_focus_labels=[],
                primary_repository_ids=[],
            )
        ),
    )

    result = await routes.get_space_settings(3, current_user=current_user, db=db)

    assert result.workspace_id == 3
    assert result.display_name == "Alpha"


@pytest.mark.asyncio
async def test_patch_space_settings_maps_validation_error(monkeypatch):
    from app.routers import spaces as routes

    db = SimpleNamespace()
    current_user = SimpleNamespace(id=7)
    workspace = SimpleNamespace(id=3)
    request = routes.UpdateSpaceSettingsRequest(primary_repository_ids=[99])

    monkeypatch.setattr(routes, "get_user_workspace", AsyncMock(return_value=(workspace, "owner")))
    monkeypatch.setattr(routes, "require_workspace_role", AsyncMock())
    monkeypatch.setattr(
        routes,
        "update_space_settings",
        AsyncMock(side_effect=routes.SpaceSettingsValidationError("bad repo")),
    )

    with pytest.raises(HTTPException) as exc:
        await routes.patch_space_settings(3, request, current_user=current_user, db=db)

    assert exc.value.status_code == 400
    assert exc.value.detail == "bad repo"
