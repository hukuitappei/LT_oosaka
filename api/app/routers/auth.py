from __future__ import annotations

from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import User
from app.db.session import get_db
from app.dependencies import get_current_user
from app.schemas.auth import TokenResponse, UserResponse
from app.services.github_oauth import (
    GitHubOAuthEmailUnavailableError,
    GitHubOAuthNotConfiguredError,
    GitHubOAuthTokenExchangeError,
    complete_github_login,
)
from app.services.user_sessions import (
    InvalidCredentialsError,
    UserAlreadyExistsError,
    get_user_profile,
    login_user,
    register_user,
)

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: str
    password: str


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    try:
        return await register_user(db, request.email, request.password)
    except UserAlreadyExistsError:
        raise HTTPException(status_code=400, detail="Email already registered")


@router.post("/login", response_model=TokenResponse)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await login_user(db, form.username, form.password)
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.get("/github/start")
async def github_oauth_start(
    redirect_uri: str | None = Query(default=None),
):
    if not settings.github_oauth_client_id:
        raise HTTPException(status_code=400, detail="GitHub OAuth is not configured")

    query = urlencode(
        {
            "client_id": settings.github_oauth_client_id,
            "redirect_uri": redirect_uri or settings.github_oauth_redirect_uri,
            "scope": "read:user user:email",
        }
    )
    return RedirectResponse(f"https://github.com/login/oauth/authorize?{query}")


@router.get("/github/callback", response_model=TokenResponse)
async def github_oauth_callback(
    code: str,
    redirect_uri: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await complete_github_login(db, code, redirect_uri=redirect_uri)
    except (
        GitHubOAuthNotConfiguredError,
        GitHubOAuthTokenExchangeError,
        GitHubOAuthEmailUnavailableError,
    ) as exc:
        detail = "GitHub OAuth is not configured"
        if isinstance(exc, GitHubOAuthTokenExchangeError):
            detail = "GitHub OAuth token exchange failed"
        elif isinstance(exc, GitHubOAuthEmailUnavailableError):
            detail = "GitHub account email not available"
        raise HTTPException(status_code=400, detail=detail)


@router.get("/me", response_model=UserResponse)
async def me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_user_profile(db, current_user)
