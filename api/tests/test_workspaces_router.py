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
async def test_list_workspaces_returns_service_rows(monkeypatch):
    from app.routers import workspaces as routes

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

    result = await routes.list_workspaces(current_user=current_user, db=db)

    assert len(result) == 1
    assert result[0].id == 3
    assert result[0].role == "admin"
    routes.list_user_workspaces.assert_awaited_once_with(db, 7)


@pytest.mark.asyncio
async def test_get_workspace_returns_404_when_membership_missing(monkeypatch):
    from app.routers import workspaces as routes

    db = SimpleNamespace()
    current_user = SimpleNamespace(id=7)

    monkeypatch.setattr(
        routes,
        "get_user_workspace",
        AsyncMock(side_effect=routes.WorkspaceNotFoundError),
    )

    with pytest.raises(HTTPException) as exc:
        await routes.get_workspace(11, current_user=current_user, db=db)

    assert exc.value.status_code == 404
    routes.get_user_workspace.assert_awaited_once_with(db, 11, 7)


@pytest.mark.asyncio
async def test_add_workspace_member_maps_service_errors(monkeypatch):
    from app.routers import workspaces as routes

    db = SimpleNamespace()
    current_user = SimpleNamespace(id=7)
    request = routes.AddMemberRequest(email="member@example.com", role="member")

    monkeypatch.setattr(
        routes,
        "add_workspace_member_to_workspace",
        AsyncMock(side_effect=routes.WorkspaceMemberAlreadyExistsError),
    )

    with pytest.raises(HTTPException) as exc:
        await routes.add_workspace_member(3, request, current_user=current_user, db=db)

    assert exc.value.status_code == 400
    routes.add_workspace_member_to_workspace.assert_awaited_once_with(
        db,
        workspace_id=3,
        actor_user_id=7,
        email="member@example.com",
        role="member",
    )


@pytest.mark.asyncio
async def test_add_workspace_member_maps_permission_and_not_found_errors(monkeypatch):
    from app.routers import workspaces as routes

    db = SimpleNamespace()
    current_user = SimpleNamespace(id=7)
    request = routes.AddMemberRequest(email="member@example.com", role="member")

    monkeypatch.setattr(
        routes,
        "add_workspace_member_to_workspace",
        AsyncMock(side_effect=routes.WorkspacePermissionError),
    )

    with pytest.raises(HTTPException) as exc:
        await routes.add_workspace_member(3, request, current_user=current_user, db=db)

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_update_workspace_member_maps_service_errors(monkeypatch):
    from app.routers import workspaces as routes

    db = SimpleNamespace()
    current_user = SimpleNamespace(id=7)
    request = routes.UpdateMemberRequest(role="admin")

    monkeypatch.setattr(
        routes,
        "update_workspace_member_role_in_workspace",
        AsyncMock(side_effect=routes.WorkspaceMemberNotFoundError),
    )

    with pytest.raises(HTTPException) as exc:
        await routes.update_workspace_member(3, 9, request, current_user=current_user, db=db)

    assert exc.value.status_code == 404
    routes.update_workspace_member_role_in_workspace.assert_awaited_once_with(
        db,
        workspace_id=3,
        actor_user_id=7,
        target_user_id=9,
        role="admin",
    )


@pytest.mark.asyncio
async def test_update_workspace_member_maps_permission_error(monkeypatch):
    from app.routers import workspaces as routes

    db = SimpleNamespace()
    current_user = SimpleNamespace(id=7)
    request = routes.UpdateMemberRequest(role="admin")

    monkeypatch.setattr(
        routes,
        "update_workspace_member_role_in_workspace",
        AsyncMock(side_effect=routes.WorkspacePermissionError),
    )

    with pytest.raises(HTTPException) as exc:
        await routes.update_workspace_member(3, 9, request, current_user=current_user, db=db)

    assert exc.value.status_code == 403
