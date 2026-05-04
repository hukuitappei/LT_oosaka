from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest


@pytest.mark.asyncio
async def test_get_workspace_pull_request_returns_workspace_pr(db_session):
    from app.db.models import PullRequest, Repository, Workspace
    from app.services.pull_requests import get_workspace_pull_request

    workspace = Workspace(name="ws", slug="ws", is_personal=True)
    other_workspace = Workspace(name="other", slug="other", is_personal=True)
    db_session.add_all([workspace, other_workspace])
    await db_session.flush()

    repo = Repository(workspace_id=workspace.id, github_id=1, full_name="owner/repo", name="repo")
    db_session.add(repo)
    await db_session.flush()

    pr = PullRequest(
        repository_id=repo.id,
        github_pr_number=1,
        title="title",
        body="body",
        state="merged",
        author="author",
        github_url="https://example.com",
    )
    db_session.add(pr)
    await db_session.commit()

    found = await get_workspace_pull_request(db_session, pr.id, workspace.id)
    not_found = await get_workspace_pull_request(db_session, pr.id, other_workspace.id)

    assert found is not None
    assert found.id == pr.id
    assert not_found is None


@pytest.mark.asyncio
async def test_request_reanalysis_for_pull_request_enqueues_task(monkeypatch, db_session):
    from app.db.models import PullRequest, Repository, Workspace
    from app.services.pull_requests import request_reanalysis_for_pull_request

    workspace = Workspace(name="ws", slug="ws", is_personal=True)
    db_session.add(workspace)
    await db_session.flush()

    repo = Repository(workspace_id=workspace.id, github_id=1, full_name="owner/repo", name="repo")
    db_session.add(repo)
    await db_session.flush()

    pr = PullRequest(
        repository_id=repo.id,
        github_pr_number=1,
        title="title",
        body="body",
        state="merged",
        author="author",
        github_url="https://example.com",
    )
    db_session.add(pr)
    await db_session.commit()

    delay_mock = MagicMock()
    monkeypatch.setattr("app.tasks.extract.reanalyze_pr_task.delay", delay_mock)

    result = await request_reanalysis_for_pull_request(db_session, pr.id, workspace.id, 7)

    assert result == {"status": "accepted", "pr_id": pr.id}
    delay_mock.assert_called_once_with({"pr_id": pr.id, "workspace_id": workspace.id, "user_id": 7})


@pytest.mark.asyncio
async def test_record_learning_reuse_for_pull_request_creates_event(db_session):
    from app.db.models import LearningItem, PullRequest, Repository, Workspace
    from app.services.pull_requests import record_learning_reuse_for_pull_request

    workspace = Workspace(name="ws", slug="ws-reuse", is_personal=True)
    db_session.add(workspace)
    await db_session.flush()

    repo = Repository(workspace_id=workspace.id, github_id=1, full_name="owner/repo", name="repo")
    db_session.add(repo)
    await db_session.flush()

    source_pr = PullRequest(
        repository_id=repo.id,
        github_pr_number=1,
        title="Older PR",
        body="body",
        state="merged",
        author="author",
        github_url="https://example.com/pr/1",
    )
    target_pr = PullRequest(
        repository_id=repo.id,
        github_pr_number=2,
        title="Newer PR",
        body="body",
        state="merged",
        author="author",
        github_url="https://example.com/pr/2",
    )
    db_session.add_all([source_pr, target_pr])
    await db_session.flush()

    item = LearningItem(
        workspace_id=workspace.id,
        pull_request_id=source_pr.id,
        schema_version="1.0",
        title="Validate before persistence",
        detail="detail",
        category="design",
        confidence=0.9,
        action_for_next_time="act",
        evidence="evidence",
        status="applied",
        visibility="workspace_shared",
    )
    db_session.add(item)
    await db_session.commit()

    result = await record_learning_reuse_for_pull_request(
        db_session,
        source_learning_item_id=item.id,
        target_pr_id=target_pr.id,
        workspace_id=workspace.id,
        user_id=7,
    )

    assert result["source_learning_item_id"] == item.id
    assert result["target_pull_request_id"] == target_pr.id
    assert result["reuse_count"] == 1
    assert result["already_recorded"] is False


@pytest.mark.asyncio
async def test_get_related_learning_items_for_pull_request_returns_ranked_matches(db_session):
    from app.db.models import LearningItem, PullRequest, Repository, Workspace
    from app.services.pull_requests import (
        get_related_learning_items_for_pull_request,
        get_workspace_pull_request,
    )

    workspace = Workspace(name="ws", slug="ws-related", is_personal=True)
    db_session.add(workspace)
    await db_session.flush()

    repo = Repository(workspace_id=workspace.id, github_id=1, full_name="owner/repo", name="repo")
    other_repo = Repository(workspace_id=workspace.id, github_id=2, full_name="owner/other", name="other")
    db_session.add_all([repo, other_repo])
    await db_session.flush()

    current_pr = PullRequest(
        repository_id=repo.id,
        github_pr_number=1,
        title="Tighten request validation and persistence boundaries",
        body="Validation should happen before persistence in the API layer.",
        state="merged",
        author="author",
        github_url="https://example.com/pr/1",
    )
    related_pr = PullRequest(
        repository_id=repo.id,
        github_pr_number=2,
        title="Add validation to API boundary",
        body="Body",
        state="merged",
        author="author",
        github_url="https://example.com/pr/2",
    )
    weaker_pr = PullRequest(
        repository_id=other_repo.id,
        github_pr_number=3,
        title="Improve test fixtures",
        body="Body",
        state="merged",
        author="author",
        github_url="https://example.com/pr/3",
    )
    db_session.add_all([current_pr, related_pr, weaker_pr])
    await db_session.flush()

    db_session.add_all(
        [
            LearningItem(
                workspace_id=workspace.id,
                pull_request_id=current_pr.id,
                schema_version="1.0",
                title="Current item",
                detail="detail",
                category="design",
                confidence=0.9,
                action_for_next_time="act",
                evidence="evidence",
                status="new",
                visibility="workspace_shared",
            ),
            LearningItem(
                workspace_id=workspace.id,
                pull_request_id=related_pr.id,
                schema_version="1.0",
                title="Validate before persistence",
                detail="Move validation into the API layer before saving records.",
                category="design",
                confidence=0.95,
                action_for_next_time="Check boundaries first.",
                evidence="Review flagged missing validation before persistence.",
                status="applied",
                visibility="workspace_shared",
                created_at=datetime.now(timezone.utc) - timedelta(days=7),
            ),
            LearningItem(
                workspace_id=workspace.id,
                pull_request_id=weaker_pr.id,
                schema_version="1.0",
                title="Improve fixtures",
                detail="Keep fixture setup isolated for tests.",
                category="testing",
                confidence=0.7,
                action_for_next_time="act",
                evidence="test fixture issue",
                status="new",
                visibility="workspace_shared",
            ),
        ]
    )
    await db_session.commit()

    pr = await get_workspace_pull_request(db_session, current_pr.id, workspace.id)
    assert pr is not None

    matches = await get_related_learning_items_for_pull_request(db_session, pr, workspace.id)

    assert len(matches) == 1
    assert matches[0].item.pull_request_id == related_pr.id
    assert matches[0].same_repository is True
    assert "persistence" in matches[0].matched_terms
    assert "content_match" in matches[0].match_types
    assert matches[0].score > 0
    assert "Same repository context" in matches[0].recommendation_reasons
    assert "Previously marked as applied" in matches[0].recommendation_reasons


@pytest.mark.asyncio
async def test_get_related_learning_items_prioritizes_reuse_signals_over_weaker_matches(db_session):
    from app.db.models import LearningItem, PullRequest, Repository, Workspace
    from app.services.pull_requests import (
        get_related_learning_items_for_pull_request,
        get_workspace_pull_request,
    )

    workspace = Workspace(name="ws", slug="ws-priority", is_personal=True)
    db_session.add(workspace)
    await db_session.flush()

    repo = Repository(workspace_id=workspace.id, github_id=1, full_name="owner/repo", name="repo")
    other_repo = Repository(workspace_id=workspace.id, github_id=2, full_name="owner/other", name="other")
    db_session.add_all([repo, other_repo])
    await db_session.flush()

    current_pr = PullRequest(
        repository_id=repo.id,
        github_pr_number=10,
        title="Tighten validation and persistence boundaries",
        body="Validation should happen before persistence in the API layer.",
        state="merged",
        author="author",
        github_url="https://example.com/pr/10",
    )
    strong_pr = PullRequest(
        repository_id=repo.id,
        github_pr_number=11,
        title="Fix persistence validation gap",
        body="Body",
        state="merged",
        author="author",
        github_url="https://example.com/pr/11",
    )
    weak_pr = PullRequest(
        repository_id=other_repo.id,
        github_pr_number=12,
        title="Validation docs refresh",
        body="Body",
        state="merged",
        author="author",
        github_url="https://example.com/pr/12",
    )
    db_session.add_all([current_pr, strong_pr, weak_pr])
    await db_session.flush()

    db_session.add(
        LearningItem(
            workspace_id=workspace.id,
            pull_request_id=current_pr.id,
            schema_version="1.0",
            title="Current validation item",
            detail="Keep validation in the request boundary before writes.",
            category="design",
            confidence=0.92,
            action_for_next_time="act",
            evidence="evidence",
            status="new",
            visibility="workspace_shared",
        )
    )
    db_session.add_all(
        [
            LearningItem(
                workspace_id=workspace.id,
                pull_request_id=strong_pr.id,
                schema_version="1.0",
                title="Validate before persistence",
                detail="Validation belongs in the API boundary before saving data.",
                category="design",
                confidence=0.96,
                action_for_next_time="Check validation before writes.",
                evidence="Review found boundary validation issues.",
                status="applied",
                visibility="workspace_shared",
                created_at=datetime.now(timezone.utc) - timedelta(days=5),
            ),
            LearningItem(
                workspace_id=workspace.id,
                pull_request_id=weak_pr.id,
                schema_version="1.0",
                title="Validation persistence docs note",
                detail="Document validation and persistence expectations for contributors.",
                category="docs",
                confidence=0.7,
                action_for_next_time="Add docs.",
                evidence="Docs issue",
                status="new",
                visibility="workspace_shared",
                created_at=datetime.now(timezone.utc) - timedelta(days=180),
            ),
        ]
    )
    await db_session.commit()

    pr = await get_workspace_pull_request(db_session, current_pr.id, workspace.id)
    assert pr is not None

    matches = await get_related_learning_items_for_pull_request(db_session, pr, workspace.id)

    assert len(matches) == 1
    assert matches[0].item.pull_request_id == strong_pr.id
    assert "content_match" in matches[0].match_types
    assert "Matches the current learning category" in matches[0].recommendation_reasons
    assert "Previously marked as applied" in matches[0].recommendation_reasons


@pytest.mark.asyncio
async def test_get_related_learning_items_uses_review_comment_and_file_path_context(db_session):
    from app.db.models import LearningItem, PullRequest, Repository, ReviewComment, Workspace
    from app.services.pull_requests import (
        get_related_learning_items_for_pull_request,
        get_workspace_pull_request,
    )

    workspace = Workspace(name="ws", slug="ws-review-context", is_personal=True)
    db_session.add(workspace)
    await db_session.flush()

    repo = Repository(workspace_id=workspace.id, github_id=1, full_name="owner/repo", name="repo")
    other_repo = Repository(workspace_id=workspace.id, github_id=2, full_name="owner/other", name="other")
    db_session.add_all([repo, other_repo])
    await db_session.flush()

    current_pr = PullRequest(
        repository_id=repo.id,
        github_pr_number=21,
        title="Refactor API endpoint",
        body="Tighten the handler implementation.",
        state="merged",
        author="author",
        github_url="https://example.com/pr/21",
    )
    related_pr = PullRequest(
        repository_id=other_repo.id,
        github_pr_number=22,
        title="Refactor serializer",
        body="Cleanup response flow.",
        state="merged",
        author="author",
        github_url="https://example.com/pr/22",
    )
    unrelated_pr = PullRequest(
        repository_id=other_repo.id,
        github_pr_number=23,
        title="Adjust dashboard layout",
        body="UI polish.",
        state="merged",
        author="author",
        github_url="https://example.com/pr/23",
    )
    db_session.add_all([current_pr, related_pr, unrelated_pr])
    await db_session.flush()

    db_session.add(
        LearningItem(
            workspace_id=workspace.id,
            pull_request_id=current_pr.id,
            schema_version="1.0",
            title="Current API item",
            detail="Keep handlers slim and move validation down.",
            category="design",
            confidence=0.9,
            action_for_next_time="act",
            evidence="evidence",
            status="new",
            visibility="workspace_shared",
        )
    )
    db_session.add_all(
        [
            LearningItem(
                workspace_id=workspace.id,
                pull_request_id=related_pr.id,
                schema_version="1.0",
                title="Keep route handlers slim",
                detail="Push validation and parsing out of the API route.",
                category="design",
                confidence=0.94,
                action_for_next_time="Move validation to a service layer.",
                evidence="Previous review flagged route concerns.",
                status="applied",
                visibility="workspace_shared",
                created_at=datetime.now(timezone.utc) - timedelta(days=10),
            ),
            LearningItem(
                workspace_id=workspace.id,
                pull_request_id=unrelated_pr.id,
                schema_version="1.0",
                title="Dashboard layout cleanup",
                detail="Tidy the card spacing.",
                category="ui",
                confidence=0.8,
                action_for_next_time="Adjust layout.",
                evidence="UI polish.",
                status="new",
                visibility="workspace_shared",
            ),
        ]
    )
    await db_session.flush()

    db_session.add_all(
        [
            ReviewComment(
                pull_request_id=current_pr.id,
                github_comment_id=1001,
                author="reviewer",
                body="Please move this validation out of the aausersroute handler into a service.",
                file_path="api/routes/aausersroute.py",
                line_number=12,
                resolved=False,
            ),
            ReviewComment(
                pull_request_id=related_pr.id,
                github_comment_id=1002,
                author="reviewer",
                body="The same aausersroute handler is doing validation work that belongs in a service.",
                file_path="api/routes/aausersroute.py",
                line_number=18,
                resolved=False,
            ),
            ReviewComment(
                pull_request_id=unrelated_pr.id,
                github_comment_id=1003,
                author="reviewer",
                body="Spacing on the dashboard cards still looks off.",
                file_path="web/src/app/page.tsx",
                line_number=8,
                resolved=False,
            ),
        ]
    )
    await db_session.commit()

    pr = await get_workspace_pull_request(db_session, current_pr.id, workspace.id)
    assert pr is not None

    matches = await get_related_learning_items_for_pull_request(db_session, pr, workspace.id)

    assert len(matches) == 1
    assert matches[0].item.pull_request_id == related_pr.id
    assert matches[0].score > 0
    assert "review_match" in matches[0].match_types
    assert "file_path_match" in matches[0].match_types
    assert "Aligned with review comment context" in matches[0].recommendation_reasons
    assert "Strong overlap on" in " ".join(matches[0].recommendation_reasons)
    assert "Previously marked as applied" in matches[0].recommendation_reasons


@pytest.mark.asyncio
async def test_get_related_learning_items_uses_review_comment_context_and_file_paths(db_session):
    from app.db.models import LearningItem, PullRequest, Repository, ReviewComment, Workspace
    from app.services.pull_requests import (
        get_related_learning_items_for_pull_request,
        get_workspace_pull_request,
    )

    workspace = Workspace(name="ws", slug="ws-review-context", is_personal=True)
    db_session.add(workspace)
    await db_session.flush()

    repo = Repository(workspace_id=workspace.id, github_id=1, full_name="owner/repo", name="repo")
    other_repo = Repository(workspace_id=workspace.id, github_id=2, full_name="owner/other", name="other")
    db_session.add_all([repo, other_repo])
    await db_session.flush()

    current_pr = PullRequest(
        repository_id=repo.id,
        github_pr_number=20,
        title="Stabilize API writes",
        body="Reduce regressions in write paths.",
        state="merged",
        author="author",
        github_url="https://example.com/pr/20",
    )
    related_pr = PullRequest(
        repository_id=other_repo.id,
        github_pr_number=21,
        title="Serializer cleanup",
        body="Refactor serializer behavior.",
        state="merged",
        author="author",
        github_url="https://example.com/pr/21",
    )
    unrelated_pr = PullRequest(
        repository_id=other_repo.id,
        github_pr_number=22,
        title="Fixture refresh",
        body="Test support cleanup.",
        state="merged",
        author="author",
        github_url="https://example.com/pr/22",
    )
    db_session.add_all([current_pr, related_pr, unrelated_pr])
    await db_session.flush()

    db_session.add_all(
        [
            ReviewComment(
                pull_request_id=current_pr.id,
                github_comment_id=1001,
                author="reviewer",
                body="Please guard this aaserializerguard write path with idempotency checks.",
                file_path="api/serializers/aaserializerguard.py",
                line_number=12,
            ),
            ReviewComment(
                pull_request_id=related_pr.id,
                github_comment_id=1002,
                author="reviewer",
                body="Aaserializerguard write path needs idempotency before retrying.",
                file_path="api/serializers/aaserializerguard.py",
                line_number=18,
            ),
            ReviewComment(
                pull_request_id=unrelated_pr.id,
                github_comment_id=1003,
                author="reviewer",
                body="Refresh fixture names.",
                file_path="tests/fixtures/users.py",
                line_number=7,
            ),
        ]
    )
    db_session.add(
        LearningItem(
            workspace_id=workspace.id,
            pull_request_id=current_pr.id,
            schema_version="1.0",
            title="Current serializer item",
            detail="Keep write paths safe during retries.",
            category="reliability",
            confidence=0.85,
            action_for_next_time="act",
            evidence="evidence",
            status="new",
            visibility="workspace_shared",
        )
    )
    db_session.add_all(
        [
            LearningItem(
                workspace_id=workspace.id,
                pull_request_id=related_pr.id,
                schema_version="1.0",
                title="Protect serializer write retries",
                detail="Idempotency checks should guard serializer writes before retry loops.",
                category="reliability",
                confidence=0.9,
                action_for_next_time="Add retry guards.",
                evidence="Review highlighted serializer retry issues.",
                status="applied",
                visibility="workspace_shared",
            ),
            LearningItem(
                workspace_id=workspace.id,
                pull_request_id=unrelated_pr.id,
                schema_version="1.0",
                title="Refresh fixtures",
                detail="Keep fixture naming consistent.",
                category="testing",
                confidence=0.7,
                action_for_next_time="Rename fixtures.",
                evidence="Fixture issue.",
                status="new",
                visibility="workspace_shared",
            ),
        ]
    )
    await db_session.commit()

    pr = await get_workspace_pull_request(db_session, current_pr.id, workspace.id)
    assert pr is not None

    matches = await get_related_learning_items_for_pull_request(db_session, pr, workspace.id)

    assert len(matches) == 1
    assert matches[0].item.pull_request_id == related_pr.id
    assert "idempotency" in matches[0].matched_terms
    assert "review_match" in matches[0].match_types
    assert "file_path_match" in matches[0].match_types
    assert "Aligned with review comment context" in matches[0].recommendation_reasons
    assert "Strong overlap on" in " ".join(matches[0].recommendation_reasons)
