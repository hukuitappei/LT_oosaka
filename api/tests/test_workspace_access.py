import sys
from pathlib import Path

import pytest

API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.db.models import User, Workspace
from app.routers.workspaces import get_current_workspace_context
from app.dependencies import get_current_workspace
from app.routers.learning_items import list_learning_items
from app.services.auth import decode_access_token
from app.services.user_sessions import register_user


@pytest.mark.asyncio
async def test_current_workspace_context_uses_header_workspace_id(db_session, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "secret_key", "test-secret", raising=False)

    created = await register_user(db_session, "dana@example.com", "pw-123456")
    payload = decode_access_token(created.access_token)
    user = await db_session.get(User, int(payload["sub"]))

    workspace = await db_session.get(Workspace, created.default_workspace_id)
    assert workspace is not None

    workspace = await get_current_workspace(
        current_user=user,
        db=db_session,
        space_header=None,
        workspace_header=workspace.id,
        space_cookie=None,
        workspace_cookie=None,
    )
    result = await get_current_workspace_context(workspace=workspace, current_user=user, db=db_session)

    assert result.id == workspace.id
    assert result.role == "owner"


@pytest.mark.asyncio
async def test_current_workspace_context_uses_header_space_id(db_session, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "secret_key", "test-secret", raising=False)

    created = await register_user(db_session, "space-header@example.com", "pw-123456")
    payload = decode_access_token(created.access_token)
    user = await db_session.get(User, int(payload["sub"]))

    workspace = await db_session.get(Workspace, created.default_workspace_id)
    assert workspace is not None

    workspace = await get_current_workspace(
        current_user=user,
        db=db_session,
        space_header=workspace.id,
        workspace_header=None,
        space_cookie=None,
        workspace_cookie=None,
    )

    assert workspace.id == created.default_space_id



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


@pytest.mark.asyncio
async def test_learning_items_include_repository_and_pull_request_context(db_session, monkeypatch):
    from app.config import settings
    from app.db.models import LearningItem, PullRequest, Repository

    monkeypatch.setattr(settings, "secret_key", "test-secret", raising=False)

    created = await register_user(db_session, "learn@example.com", "pw-123456")
    user = await db_session.get(User, int(decode_access_token(created.access_token)["sub"]))
    workspace = await db_session.get(Workspace, created.default_workspace_id)

    repo = Repository(
        workspace_id=workspace.id,
        github_id=10,
        full_name="acme/review-hub",
        name="review-hub",
    )
    db_session.add(repo)
    await db_session.flush()

    pr = PullRequest(
        repository_id=repo.id,
        github_pr_number=42,
        title="Tighten validation",
        body="body",
        state="merged",
        author="alice",
        github_url="https://github.com/acme/review-hub/pull/42",
    )
    db_session.add(pr)
    await db_session.flush()

    item = LearningItem(
        workspace_id=workspace.id,
        pull_request_id=pr.id,
        schema_version="1.0",
        title="Validate before persistence",
        detail="Reject malformed payloads before saving them.",
        category="design",
        confidence=0.9,
        action_for_next_time="Add boundary validation in the request layer.",
        evidence="The review pointed out missing validation.",
    )
    db_session.add(item)
    await db_session.commit()

    result = await list_learning_items(
        db=db_session,
        current_user=user,
        current_workspace=workspace,
    )

    assert len(result) == 1
    assert result[0].repository.full_name == "acme/review-hub"
    assert result[0].pull_request.github_pr_number == 42
