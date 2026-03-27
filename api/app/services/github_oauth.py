from __future__ import annotations

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import User
from app.services.auth import hash_password
from app.services.user_sessions import build_token_response
from app.services.workspaces import ensure_personal_workspace


class GitHubOAuthNotConfiguredError(Exception):
    pass


class GitHubOAuthTokenExchangeError(Exception):
    pass


class GitHubOAuthEmailUnavailableError(Exception):
    pass


async def _exchange_github_code(
    client: httpx.AsyncClient,
    code: str,
    redirect_uri: str | None,
) -> str:
    token_response = await client.post(
        "https://github.com/login/oauth/access_token",
        headers={"Accept": "application/json"},
        data={
            "client_id": settings.github_oauth_client_id,
            "client_secret": settings.github_oauth_client_secret,
            "code": code,
            "redirect_uri": redirect_uri or settings.github_oauth_redirect_uri,
        },
    )
    token_response.raise_for_status()
    token_payload = token_response.json()
    access_token = token_payload.get("access_token")
    if not access_token:
        raise GitHubOAuthTokenExchangeError
    return access_token


async def _fetch_github_user(
    client: httpx.AsyncClient,
    access_token: str,
) -> dict:
    user_response = await client.get(
        "https://api.github.com/user",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github+json",
        },
    )
    user_response.raise_for_status()
    return user_response.json()


async def _resolve_primary_email(
    client: httpx.AsyncClient,
    access_token: str,
    github_user: dict,
) -> str:
    primary_email = github_user.get("email")
    if primary_email:
        return primary_email

    emails_response = await client.get(
        "https://api.github.com/user/emails",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github+json",
        },
    )
    emails_response.raise_for_status()
    emails = emails_response.json()
    primary = next((item for item in emails if item.get("primary")), None)
    primary_email = primary["email"] if primary else None
    if not primary_email:
        raise GitHubOAuthEmailUnavailableError
    return primary_email


async def complete_github_login(
    db: AsyncSession,
    code: str,
    *,
    redirect_uri: str | None = None,
) -> "TokenResponse":
    if not settings.github_oauth_client_id or not settings.github_oauth_client_secret:
        raise GitHubOAuthNotConfiguredError

    async with httpx.AsyncClient() as client:
        access_token = await _exchange_github_code(client, code, redirect_uri)
        github_user = await _fetch_github_user(client, access_token)
        primary_email = await _resolve_primary_email(client, access_token, github_user)

    user = await db.scalar(select(User).where(User.github_user_id == github_user["id"]))
    if user is None:
        user = await db.scalar(select(User).where(User.email == primary_email))

    if user is None:
        user = User(
            email=primary_email,
            hashed_password=hash_password(primary_email + str(github_user["id"])),
            github_user_id=github_user["id"],
            github_login=github_user.get("login"),
        )
        db.add(user)
        await db.flush()
        await ensure_personal_workspace(db, user)
    else:
        user.github_user_id = github_user["id"]
        user.github_login = github_user.get("login")

    await db.commit()
    await db.refresh(user)
    return await build_token_response(db, user)
