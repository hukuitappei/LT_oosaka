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
from app.services.github_oauth import complete_github_login
from app.services.auth import create_access_token, decode_access_token, hash_password, verify_password
from app.services.user_sessions import get_user_profile, login_user, register_user


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

    response = await register_user(db_session, "alice@example.com", "pw-123456")
    assert response.default_space_id == response.default_workspace_id
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

    created = await register_user(db_session, "bob@example.com", "pw-123456")
    logged_in = await login_user(db_session, "bob@example.com", "pw-123456")

    assert logged_in.default_space_id == created.default_space_id
    assert logged_in.default_workspace_id == created.default_workspace_id


@pytest.mark.asyncio
async def test_me_includes_workspace_memberships(db_session, monkeypatch):
    monkeypatch.setattr(settings, "secret_key", "test-secret", raising=False)

    created = await register_user(db_session, "carol@example.com", "pw-123456")
    payload = decode_access_token(created.access_token)
    user = await db_session.get(User, int(payload["sub"]))

    profile = await get_user_profile(db_session, user)

    assert profile.email == "carol@example.com"
    assert len(profile.spaces) == 1
    assert profile.spaces[0].is_personal is True
    assert profile.spaces[0].role == "owner"
    assert len(profile.workspaces) == 1
    assert profile.workspaces[0].is_personal is True
    assert profile.workspaces[0].role == "owner"


@pytest.mark.asyncio
async def test_complete_github_login_creates_user_and_workspace(db_session, monkeypatch):
    monkeypatch.setattr(settings, "secret_key", "test-secret", raising=False)
    monkeypatch.setattr(settings, "github_oauth_client_id", "client-id", raising=False)
    monkeypatch.setattr(settings, "github_oauth_client_secret", "client-secret", raising=False)
    monkeypatch.setattr(settings, "github_oauth_redirect_uri", "http://localhost/callback", raising=False)

    class FakeResponse:
        def __init__(self, payload):
            self._payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self._payload

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, headers, data):
            return FakeResponse({"access_token": "github-token"})

        async def get(self, url, headers):
            if url.endswith("/user"):
                return FakeResponse({"id": 123, "login": "octocat", "email": "octo@example.com"})
            return FakeResponse([])

    monkeypatch.setattr("app.services.github_oauth.httpx.AsyncClient", FakeClient)

    response = await complete_github_login(db_session, "auth-code")
    assert response.default_space_id == response.default_workspace_id
    payload = decode_access_token(response.access_token)
    user = await db_session.get(User, int(payload["sub"]))

    assert user is not None
    assert user.github_user_id == 123
    assert user.github_login == "octocat"

    workspace = await db_session.get(Workspace, response.default_workspace_id)
    assert workspace is not None
    assert workspace.is_personal is True
