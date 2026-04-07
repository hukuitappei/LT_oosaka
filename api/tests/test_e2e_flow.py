from __future__ import annotations

import sys
from pathlib import Path

import httpx
import pytest

API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.db import models as _models  # noqa: F401


@pytest.mark.asyncio
async def test_auth_workspace_learning_items_and_digests_flow(db_session, monkeypatch):
    from app.config import settings
    from app.db.models import LearningItem, PullRequest, Repository, WeeklyDigest, Workspace
    from app.db.session import get_db
    from app.factory import create_app
    from app.routers.auth import get_db as auth_get_db
    from app.routers.learning_items import get_db as learning_items_get_db
    from app.routers.weekly_digests import get_db as weekly_digests_get_db
    from app.routers.workspaces import get_db as workspaces_get_db

    monkeypatch.setattr(settings, "secret_key", "test-secret", raising=False)
    app = create_app()

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[auth_get_db] = override_get_db
    app.dependency_overrides[workspaces_get_db] = override_get_db
    app.dependency_overrides[learning_items_get_db] = override_get_db
    app.dependency_overrides[weekly_digests_get_db] = override_get_db

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        register_response = await client.post(
            "/auth/register",
            json={"email": "e2e@example.com", "password": "pw-123456"},
        )
        assert register_response.status_code == 201
        register_payload = register_response.json()
        assert register_payload["default_space_id"] == register_payload["default_workspace_id"]
        workspace_id = register_payload["default_workspace_id"]
        token = register_payload["access_token"]

        login_response = await client.post(
            "/auth/login",
            data={"username": "e2e@example.com", "password": "pw-123456"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert login_response.status_code == 200
        login_payload = login_response.json()
        assert login_payload["default_space_id"] == workspace_id
        assert login_payload["default_workspace_id"] == workspace_id

        workspace = await db_session.get(Workspace, workspace_id)
        assert workspace is not None

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
            visibility="workspace_shared",
        )
        db_session.add(item)

        digest = WeeklyDigest(
            workspace_id=workspace.id,
            year=2026,
            week=13,
            summary="Validation and API boundary handling improved.",
            repeated_issues=[],
            next_time_notes=["Keep boundary validation early."],
            pr_count=1,
            learning_count=1,
            visibility="workspace_shared",
        )
        db_session.add(digest)
        await db_session.commit()

        auth_headers = {
            "Authorization": f"Bearer {token}",
            "X-Workspace-Id": str(workspace_id),
        }

        me_response = await client.get("/auth/me", headers=auth_headers)
        assert me_response.status_code == 200
        assert me_response.json()["email"] == "e2e@example.com"

        workspace_response = await client.get("/workspaces/current/context", headers=auth_headers)
        assert workspace_response.status_code == 200
        assert workspace_response.json()["id"] == workspace_id

        space_response = await client.get(
            "/spaces/current/context",
            headers={"Authorization": f"Bearer {token}", "X-Space-Id": str(workspace_id)},
        )
        assert space_response.status_code == 200
        assert space_response.json()["id"] == workspace_id

        items_response = await client.get("/learning-items/", headers=auth_headers)
        assert items_response.status_code == 200
        items_payload = items_response.json()
        assert len(items_payload) == 1
        assert items_payload[0]["repository"]["full_name"] == "acme/review-hub"
        assert items_payload[0]["pull_request"]["github_pr_number"] == 42

        digests_response = await client.get("/weekly-digests/", headers=auth_headers)
        assert digests_response.status_code == 200
        digests_payload = digests_response.json()
        assert len(digests_payload) == 1
        assert digests_payload[0]["summary"] == "Validation and API boundary handling improved."

    app.dependency_overrides.clear()
