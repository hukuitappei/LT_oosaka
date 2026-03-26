import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import select

API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.db.models import User, Workspace, WorkspaceMember
from app.routers.auth import RegisterRequest, login, register
from app.routers.workspaces import (
    AddMemberRequest,
    CreateWorkspaceRequest,
    UpdateMemberRequest,
    add_workspace_member,
    create_workspace_endpoint,
    get_current_workspace_context,
    get_workspace,
    list_workspaces,
    update_workspace_member,
)
from app.dependencies import get_current_workspace
from app.services.auth import decode_access_token


@pytest.mark.asyncio
async def test_register_creates_personal_workspace_and_default_workspace_id(db_session, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "secret_key", "test-secret", raising=False)

    response = await register(
        RegisterRequest(email="alice@example.com", password="pw-123456"),
        db_session,
    )
    payload = decode_access_token(response.access_token)

    user = await db_session.get(User, int(payload["sub"]))
    assert user is not None
    assert response.default_workspace_id > 0

    workspace = await db_session.get(Workspace, response.default_workspace_id)
    assert workspace is not None
    assert workspace.is_personal is True

    member = await db_session.scalar(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace.id,
            WorkspaceMember.user_id == user.id,
        )
    )
    assert member is not None


@pytest.mark.asyncio
async def test_login_reuses_default_workspace_id(db_session, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "secret_key", "test-secret", raising=False)

    created = await register(
        RegisterRequest(email="bob@example.com", password="pw-123456"),
        db_session,
    )
    login_form = SimpleNamespace(username="bob@example.com", password="pw-123456")
    logged_in = await login(login_form, db_session)

    assert logged_in.default_workspace_id == created.default_workspace_id


@pytest.mark.asyncio
async def test_me_lists_workspace_memberships(db_session, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "secret_key", "test-secret", raising=False)

    created = await register(
        RegisterRequest(email="carol@example.com", password="pw-123456"),
        db_session,
    )
    payload = decode_access_token(created.access_token)
    user = await db_session.get(User, int(payload["sub"]))

    result = await list_workspaces(current_user=user, db=db_session)

    assert len(result) == 1
    assert result[0].is_personal is True
    assert result[0].role == "owner"


@pytest.mark.asyncio
async def test_current_workspace_context_uses_header_workspace_id(db_session, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "secret_key", "test-secret", raising=False)

    created = await register(
        RegisterRequest(email="dana@example.com", password="pw-123456"),
        db_session,
    )
    payload = decode_access_token(created.access_token)
    user = await db_session.get(User, int(payload["sub"]))

    workspace = await db_session.get(Workspace, created.default_workspace_id)
    assert workspace is not None

    workspace = await get_current_workspace(
        current_user=user,
        db=db_session,
        workspace_header=workspace.id,
        workspace_cookie=None,
    )
    result = await get_current_workspace_context(workspace=workspace, current_user=user, db=db_session)

    assert result.id == workspace.id
    assert result.role == "owner"


@pytest.mark.asyncio
async def test_create_workspace_and_add_member(db_session, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "secret_key", "test-secret", raising=False)

    owner_response = await register(
        RegisterRequest(email="owner@example.com", password="pw-123456"),
        db_session,
    )
    member_response = await register(
        RegisterRequest(email="member@example.com", password="pw-123456"),
        db_session,
    )
    owner = await db_session.get(User, int(decode_access_token(owner_response.access_token)["sub"]))
    member = await db_session.get(User, int(decode_access_token(member_response.access_token)["sub"]))

    created = await create_workspace_endpoint(
        CreateWorkspaceRequest(name="Team Alpha"),
        current_user=owner,
        db=db_session,
    )
    assert created.role == "owner"

    added = await add_workspace_member(
        created.id,
        AddMemberRequest(email=member.email, role="member"),
        current_user=owner,
        db=db_session,
    )
    assert added == {"status": "added"}

    updated = await update_workspace_member(
        created.id,
        member.id,
        UpdateMemberRequest(role="admin"),
        current_user=owner,
        db=db_session,
    )
    assert updated == {"status": "updated"}

    workspace = await get_workspace(created.id, current_user=member, db=db_session)
    assert workspace.id == created.id


@pytest.mark.asyncio
async def test_repository_routes_require_workspace_scope(db_session):
    from app.routers.repositories import list_repositories
    from app.services.workspaces import create_workspace

    user = User(email="legacy@example.com", hashed_password="hashed::pw")
    db_session.add(user)
    await db_session.flush()
    workspace = await create_workspace(db_session, name="Scoped", owner=user)
    await db_session.commit()

    result = await list_repositories(
        db=db_session,
        current_user=user,
        current_workspace=workspace,
    )

    assert result == []
