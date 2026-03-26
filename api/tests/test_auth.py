import sys
from pathlib import Path
from types import SimpleNamespace

API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

import pytest
from sqlalchemy import select

from app.config import settings
from app.db.models import User, Workspace, WorkspaceMember
from app.routers.auth import RegisterRequest, login, me, register
from app.services.auth import create_access_token, decode_access_token, hash_password, verify_password


@pytest.mark.asyncio
async def test_password_hash_round_trip():
    hashed = hash_password("s3cret-pass")

    assert hashed != "s3cret-pass"
    assert verify_password("s3cret-pass", hashed)


@pytest.mark.asyncio
async def test_create_access_token_encodes_user_identity(monkeypatch):
    monkeypatch.setattr(settings, "secret_key", "test-secret", raising=False)

    token = create_access_token(42, "user@example.com")
    payload = decode_access_token(token)

    assert payload["sub"] == "42"
    assert payload["email"] == "user@example.com"


@pytest.mark.asyncio
async def test_register_creates_personal_workspace(db_session, monkeypatch):
    monkeypatch.setattr(settings, "secret_key", "test-secret", raising=False)

    response = await register(
        RegisterRequest(email="alice@example.com", password="pw-123456"),
        db_session,
    )
    payload = decode_access_token(response.access_token)
    user = await db_session.get(User, int(payload["sub"]))
    assert user is not None

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
    assert member.role == "owner"


@pytest.mark.asyncio
async def test_login_reuses_default_workspace(db_session, monkeypatch):
    monkeypatch.setattr(settings, "secret_key", "test-secret", raising=False)

    created = await register(
        RegisterRequest(email="bob@example.com", password="pw-123456"),
        db_session,
    )
    logged_in = await login(
        SimpleNamespace(username="bob@example.com", password="pw-123456"),
        db_session,
    )

    assert logged_in.default_workspace_id == created.default_workspace_id


@pytest.mark.asyncio
async def test_me_includes_workspace_memberships(db_session, monkeypatch):
    monkeypatch.setattr(settings, "secret_key", "test-secret", raising=False)

    created = await register(
        RegisterRequest(email="carol@example.com", password="pw-123456"),
        db_session,
    )
    payload = decode_access_token(created.access_token)
    user = await db_session.get(User, int(payload["sub"]))

    profile = await me(current_user=user, db=db_session)

    assert profile.email == "carol@example.com"
    assert len(profile.workspaces) == 1
    assert profile.workspaces[0].is_personal is True
    assert profile.workspaces[0].role == "owner"
