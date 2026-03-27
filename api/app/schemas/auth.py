from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


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
