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
async def test_register_maps_duplicate_email_to_400(monkeypatch):
    from app.routers import auth as routes

    monkeypatch.setattr(
        routes,
        "register_user",
        AsyncMock(side_effect=routes.UserAlreadyExistsError),
    )

    with pytest.raises(HTTPException) as exc:
        await routes.register(routes.RegisterRequest(email="alice@example.com", password="pw"), db=SimpleNamespace())

    assert exc.value.status_code == 400
    assert exc.value.detail == "Email already registered"


@pytest.mark.asyncio
async def test_login_maps_invalid_credentials_to_401(monkeypatch):
    from app.routers import auth as routes

    monkeypatch.setattr(
        routes,
        "login_user",
        AsyncMock(side_effect=routes.InvalidCredentialsError),
    )

    with pytest.raises(HTTPException) as exc:
        await routes.login(SimpleNamespace(username="alice@example.com", password="bad"), db=SimpleNamespace())

    assert exc.value.status_code == 401
    assert exc.value.detail == "Incorrect email or password"


@pytest.mark.asyncio
async def test_github_callback_maps_token_exchange_error_to_400(monkeypatch):
    from app.routers import auth as routes

    monkeypatch.setattr(
        routes,
        "complete_github_login",
        AsyncMock(side_effect=routes.GitHubOAuthTokenExchangeError),
    )

    with pytest.raises(HTTPException) as exc:
        await routes.github_oauth_callback("code", db=SimpleNamespace())

    assert exc.value.status_code == 400
    assert exc.value.detail == "GitHub OAuth token exchange failed"


@pytest.mark.asyncio
async def test_me_returns_profile_from_service(monkeypatch):
    from app.routers import auth as routes
    from app.schemas.auth import SpaceSummary, UserResponse, WorkspaceSummary

    profile = UserResponse(
        id=1,
        email="alice@example.com",
        github_login="octocat",
        is_active=True,
        created_at="2026-03-27T00:00:00",
        spaces=[
            SpaceSummary(id=3, name="Alpha", slug="alpha", is_personal=False, role="admin"),
        ],
        workspaces=[
            WorkspaceSummary(id=3, name="Alpha", slug="alpha", is_personal=False, role="admin"),
        ],
    )
    monkeypatch.setattr(routes, "get_user_profile", AsyncMock(return_value=profile))

    response = await routes.me(current_user=SimpleNamespace(), db=SimpleNamespace())

    assert response.email == "alice@example.com"
    assert response.spaces[0].slug == "alpha"
    assert response.workspaces[0].slug == "alpha"
