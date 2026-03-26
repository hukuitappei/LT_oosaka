from __future__ import annotations

from datetime import datetime
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import User, Workspace, WorkspaceMember
from app.db.session import get_db
from app.dependencies import get_current_user
from app.services.auth import create_access_token, hash_password, verify_password
from app.services.workspaces import ensure_personal_workspace

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    default_workspace_id: int


class WorkspaceSummary(BaseModel):
    id: int
    name: str
    slug: str
    is_personal: bool
    role: str


class UserResponse(BaseModel):
    id: int
    email: str
    github_login: str | None
    is_active: bool
    created_at: datetime
    workspaces: list[WorkspaceSummary]


async def _build_token_response(user: User, db: AsyncSession) -> TokenResponse:
    workspace = await ensure_personal_workspace(db, user)
    await db.commit()
    await db.refresh(workspace)
    return TokenResponse(
        access_token=create_access_token(user.id, user.email),
        default_workspace_id=workspace.id,
    )


async def _load_workspace_summaries(user_id: int, db: AsyncSession) -> list[WorkspaceSummary]:
    result = await db.execute(
        select(Workspace, WorkspaceMember.role)
        .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
        .where(WorkspaceMember.user_id == user_id)
        .order_by(Workspace.is_personal.desc(), Workspace.name.asc())
    )
    return [
        WorkspaceSummary(
            id=workspace.id,
            name=workspace.name,
            slug=workspace.slug,
            is_personal=workspace.is_personal,
            role=role,
        )
        for workspace, role in result.all()
    ]


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    existing = await db.scalar(select(User).where(User.email == request.email))
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        email=request.email,
        hashed_password=hash_password(request.password),
    )
    db.add(user)
    await db.flush()
    await ensure_personal_workspace(db, user)
    await db.commit()
    await db.refresh(user)
    return await _build_token_response(user, db)


@router.post("/login", response_model=TokenResponse)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    user = await db.scalar(select(User).where(User.email == form.username))
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return await _build_token_response(user, db)


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
    if not settings.github_oauth_client_id or not settings.github_oauth_client_secret:
        raise HTTPException(status_code=400, detail="GitHub OAuth is not configured")

    async with httpx.AsyncClient() as client:
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
            raise HTTPException(status_code=400, detail="GitHub OAuth token exchange failed")

        user_response = await client.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github+json",
            },
        )
        user_response.raise_for_status()
        github_user = user_response.json()

        primary_email = github_user.get("email")
        if not primary_email:
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
        raise HTTPException(status_code=400, detail="GitHub account email not available")

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
    return await _build_token_response(user, db)


@router.get("/me", response_model=UserResponse)
async def me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        github_login=current_user.github_login,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        workspaces=await _load_workspace_summaries(current_user.id, db),
    )
