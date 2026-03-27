import hashlib
import hmac
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.config import settings
from app.db.models import LearningItem, PullRequest, Repository, Workspace
from app.github.webhook import verify_signature


class FakeRequest:
    def __init__(self, body: bytes, headers: dict[str, str]):
        self._body = body
        self.headers = headers

    async def body(self) -> bytes:
        return self._body


async def _create_pr_with_learning_item(db_session, week: int = 12):
    workspace = Workspace(
        name="Alice Workspace",
        slug="alice-workspace",
        is_personal=True,
        created_at=datetime(2026, 3, 17, tzinfo=timezone.utc),
    )
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    repo = Repository(
        workspace_id=workspace.id,
        github_id=1,
        full_name="alice/repo",
        name="repo",
        created_at=datetime(2026, 3, 18, tzinfo=timezone.utc),
    )
    db_session.add(repo)
    await db_session.commit()
    await db_session.refresh(repo)

    pr = PullRequest(
        repository_id=repo.id,
        github_pr_number=1,
        title="pr",
        body="body",
        state="merged",
        author="alice",
        github_url="https://example.com/1",
        created_at=datetime(2026, 3, 19, tzinfo=timezone.utc),
    )
    db_session.add(pr)
    await db_session.commit()
    await db_session.refresh(pr)

    item = LearningItem(
        workspace_id=workspace.id,
        pull_request_id=pr.id,
        schema_version="1.0",
        title="lesson",
        detail="detail",
        category="design",
        confidence=0.9,
        action_for_next_time="act",
        evidence="evidence",
        created_at=datetime(2026, 3, 20, tzinfo=timezone.utc),
    )
    db_session.add(item)
    await db_session.commit()
    return pr, item


@pytest.mark.asyncio
async def test_verify_signature_accepts_valid_signature(monkeypatch):
    monkeypatch.setattr(settings, "github_webhook_secret", "secret", raising=False)
    body = b'{"ping":true}'
    signature = "sha256=" + hmac.new(b"secret", body, hashlib.sha256).hexdigest()

    request = FakeRequest(body, {"X-Hub-Signature-256": signature})
    verified = await verify_signature(request)

    assert verified == body


@pytest.mark.asyncio
async def test_verify_signature_rejects_invalid_signature(monkeypatch):
    monkeypatch.setattr(settings, "github_webhook_secret", "secret", raising=False)

    request = FakeRequest(b"{}", {"X-Hub-Signature-256": "sha256=bad"})

    with pytest.raises(HTTPException) as exc:
        await verify_signature(request)

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_github_webhook_enqueues_review_comment_via_celery(monkeypatch, caplog):
    async def fake_verify_signature(request):
        return json.dumps(
            {
                "action": "created",
                "pull_request": {"merged": True, "number": 42},
                "repository": {"full_name": "alice/repo"},
            }
        ).encode("utf-8")

    from app.routers.webhook import github_webhook

    delay_mock = MagicMock()
    request = FakeRequest(b"", {"X-GitHub-Event": "pull_request_review_comment"})

    monkeypatch.setattr("app.routers.webhook.verify_signature", fake_verify_signature)
    monkeypatch.setattr("app.routers.webhook.extract_pr_task.delay", delay_mock)

    with caplog.at_level(logging.INFO):
        response = await github_webhook(request)

    delay_mock.assert_called_once()
    assert response == {"status": "accepted"}
    assert any(
        "Webhook received event_type=pull_request_review_comment action=created repo=alice/repo pr_number=42"
        in record.message
        for record in caplog.records
    )
    assert any(
        "Webhook enqueued Celery task task=extract_pr_task event_type=pull_request_review_comment action=created repo=alice/repo pr_number=42"
        in record.message
        for record in caplog.records
    )


@pytest.mark.asyncio
async def test_github_webhook_enqueues_merged_pull_request_via_celery(monkeypatch, caplog):
    async def fake_verify_signature(request):
        return json.dumps(
            {
                "action": "closed",
                "pull_request": {"merged": True, "number": 7},
                "repository": {"full_name": "alice/repo"},
                "installation": {"id": 99},
            }
        ).encode("utf-8")

    from app.routers.webhook import github_webhook

    delay_mock = MagicMock()
    request = FakeRequest(b"", {"X-GitHub-Event": "pull_request"})

    monkeypatch.setattr("app.routers.webhook.verify_signature", fake_verify_signature)
    monkeypatch.setattr("app.routers.webhook.extract_pr_task.delay", delay_mock)

    with caplog.at_level(logging.INFO):
        response = await github_webhook(request)

    delay_mock.assert_called_once()
    assert response == {"status": "accepted"}
    assert any(
        "Webhook enqueued Celery task task=extract_pr_task event_type=pull_request action=closed repo=alice/repo pr_number=7"
        in record.message
        for record in caplog.records
    )


@pytest.mark.asyncio
async def test_github_webhook_does_not_enqueue_irrelevant_event(monkeypatch, caplog):
    async def fake_verify_signature(request):
        return json.dumps(
            {
                "action": "opened",
                "pull_request": {"merged": False},
                "repository": {"full_name": "alice/repo"},
            }
        ).encode("utf-8")

    from app.routers.webhook import github_webhook

    delay_mock = MagicMock()
    request = FakeRequest(b"", {"X-GitHub-Event": "issues"})

    monkeypatch.setattr("app.routers.webhook.verify_signature", fake_verify_signature)
    monkeypatch.setattr("app.routers.webhook.extract_pr_task.delay", delay_mock)

    with caplog.at_level(logging.INFO):
        response = await github_webhook(request)

    delay_mock.assert_not_called()
    assert response == {"status": "accepted"}
    assert any(
        "Webhook ignored event_type=issues action=opened repo=alice/repo pr_number=None" in record.message
        for record in caplog.records
    )


@pytest.mark.asyncio
async def test_fetch_learning_items_for_week_returns_week_scoped_items(db_session):
    from app.services.digest_generator import fetch_learning_items_for_week

    _, item = await _create_pr_with_learning_item(db_session)

    items = await fetch_learning_items_for_week(2026, 12, item.workspace_id, db_session)

    assert [row.id for row in items] == [item.id]


@pytest.mark.asyncio
async def test_generate_digest_route_requires_llm_provider(monkeypatch, db_session):
    try:
        from app.routers.weekly_digests import generate_digest
    except ModuleNotFoundError:
        pytest.xfail("weekly digest route is not importable in the current branch")

    monkeypatch.setattr(settings, "anthropic_api_key", "", raising=False)
    monkeypatch.setattr(settings, "ollama_base_url", "", raising=False)

    from app.db.models import LearningItem, PullRequest, Repository, User, Workspace, WorkspaceMember

    owner = User(email="digest-owner@example.com", hashed_password="hashed::pw")
    workspace = Workspace(name="Digest Workspace", slug="digest-workspace", is_personal=True)
    db_session.add_all([owner, workspace])
    await db_session.flush()
    db_session.add(WorkspaceMember(workspace_id=workspace.id, user_id=owner.id, role="owner"))
    await db_session.commit()

    with pytest.raises(HTTPException) as exc:
        await generate_digest(
            SimpleNamespace(year=2026, week=12),
            db=db_session,
            current_user=owner,
            current_workspace=workspace,
        )

    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_generate_weekly_digest_persists_workspace_digest(db_session):
    from app.llm.base import BaseLLMProvider
    from app.services.digest_generator import generate_weekly_digest

    from app.db.models import User, Workspace, WorkspaceMember

    class DummyProvider(BaseLLMProvider):
        async def extract_learnings(self, pr_data):  # pragma: no cover - not used
            raise AssertionError("not called")

        async def generate_text(self, system_prompt, user_message):
            return json.dumps(
                {
                    "summary": "Weekly digest summary",
                    "repeated_issues": [],
                    "next_time_notes": [],
                }
            )

    owner = User(email="digest-owner-2@example.com", hashed_password="hashed::pw")
    workspace = Workspace(name="Digest Workspace 2", slug="digest-workspace-2", is_personal=True)
    db_session.add_all([owner, workspace])
    await db_session.flush()
    db_session.add(WorkspaceMember(workspace_id=workspace.id, user_id=owner.id, role="owner"))
    await db_session.commit()

    repo = Repository(
        workspace_id=workspace.id,
        github_id=1,
        full_name="owner/repo",
        name="repo",
    )
    db_session.add(repo)
    await db_session.flush()

    pr = PullRequest(
        repository_id=repo.id,
        github_pr_number=42,
        title="Improve validation",
        body="body",
        state="merged",
        author="author",
        github_url="https://github.com/owner/repo/pull/42",
        created_at=datetime(2026, 3, 19, tzinfo=timezone.utc),
    )
    db_session.add(pr)
    await db_session.flush()

    item = LearningItem(
        workspace_id=workspace.id,
        pull_request_id=pr.id,
        schema_version="1.0",
        title="Validate before persistence",
        detail="Check payloads before saving.",
        category="design",
        confidence=0.9,
        action_for_next_time="Validate requests earlier.",
        evidence="A review note flagged missing validation.",
        created_at=datetime(2026, 3, 20, tzinfo=timezone.utc),
    )
    db_session.add(item)
    await db_session.commit()

    digest = await generate_weekly_digest(2026, 12, workspace.id, DummyProvider(), db_session)

    assert digest.workspace_id == workspace.id
    assert digest.summary == "Weekly digest summary"
    assert digest.pr_count == 1
    assert digest.learning_count == 1


@pytest.mark.asyncio
async def test_generate_weekly_digest_logs_context(db_session, mock_llm_provider, caplog):
    from app.services.digest_generator import generate_weekly_digest

    from app.db.models import User, Workspace, WorkspaceMember

    owner = User(email="digest-owner-3@example.com", hashed_password="hashed::pw")
    workspace = Workspace(name="Digest Workspace 3", slug="digest-workspace-3", is_personal=True)
    db_session.add_all([owner, workspace])
    await db_session.flush()
    db_session.add(WorkspaceMember(workspace_id=workspace.id, user_id=owner.id, role="owner"))
    await db_session.commit()

    with caplog.at_level(logging.INFO):
        digest = await generate_weekly_digest(2026, 13, workspace.id, mock_llm_provider, db_session)

    assert digest.workspace_id == workspace.id
    assert any(
        "generate_weekly_digest started workspace_id=%d year=2026 week=13 item_count=0" % workspace.id
        in record.message
        for record in caplog.records
    )
    assert any(
        "generate_weekly_digest saved workspace_id=%d year=2026 week=13" % workspace.id in record.message
        for record in caplog.records
    )
