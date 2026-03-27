from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import LearningItem, PullRequest, Repository, User, WeeklyDigest
from app.services.auth import hash_password
from app.services.workspaces import ensure_personal_workspace


@dataclass(slots=True)
class DemoSeedResult:
    email: str
    password: str
    workspace_id: int
    repository_count: int
    pull_request_count: int
    learning_item_count: int
    digest_id: int


async def _get_or_create_user(db: AsyncSession, email: str, password: str) -> User:
    user = await db.scalar(select(User).where(User.email == email))
    if user is not None:
        return user

    user = User(
        email=email,
        hashed_password=hash_password(password),
    )
    db.add(user)
    await db.flush()
    return user


async def _get_or_create_repository(
    db: AsyncSession,
    *,
    workspace_id: int,
    github_id: int,
    full_name: str,
    name: str,
) -> Repository:
    repository = await db.scalar(
        select(Repository).where(
            Repository.workspace_id == workspace_id,
            Repository.full_name == full_name,
        )
    )
    if repository is not None:
        repository.github_id = github_id
        repository.name = name
        return repository

    repository = Repository(
        workspace_id=workspace_id,
        github_id=github_id,
        full_name=full_name,
        name=name,
    )
    db.add(repository)
    await db.flush()
    return repository


async def _get_or_create_pull_request(
    db: AsyncSession,
    *,
    repository_id: int,
    github_pr_number: int,
    title: str,
    body: str,
    author: str,
    github_url: str,
    merged_at: datetime,
) -> PullRequest:
    pull_request = await db.scalar(
        select(PullRequest).where(
            PullRequest.repository_id == repository_id,
            PullRequest.github_pr_number == github_pr_number,
        )
    )
    if pull_request is not None:
        pull_request.title = title
        pull_request.body = body
        pull_request.author = author
        pull_request.github_url = github_url
        pull_request.state = "merged"
        pull_request.merged_at = merged_at
        pull_request.processed = True
        return pull_request

    pull_request = PullRequest(
        repository_id=repository_id,
        github_pr_number=github_pr_number,
        title=title,
        body=body,
        state="merged",
        author=author,
        github_url=github_url,
        merged_at=merged_at,
        processed=True,
    )
    db.add(pull_request)
    await db.flush()
    return pull_request


async def _get_or_create_learning_item(
    db: AsyncSession,
    *,
    workspace_id: int,
    pull_request_id: int,
    title: str,
    detail: str,
    category: str,
    confidence: float,
    action_for_next_time: str,
    evidence: str,
    visibility: str,
) -> LearningItem:
    item = await db.scalar(
        select(LearningItem).where(
            LearningItem.workspace_id == workspace_id,
            LearningItem.pull_request_id == pull_request_id,
            LearningItem.title == title,
        )
    )
    if item is not None:
        item.detail = detail
        item.category = category
        item.confidence = confidence
        item.action_for_next_time = action_for_next_time
        item.evidence = evidence
        item.visibility = visibility
        return item

    item = LearningItem(
        workspace_id=workspace_id,
        pull_request_id=pull_request_id,
        schema_version="1.0",
        title=title,
        detail=detail,
        category=category,
        confidence=confidence,
        action_for_next_time=action_for_next_time,
        evidence=evidence,
        visibility=visibility,
    )
    db.add(item)
    await db.flush()
    return item


async def _get_or_create_digest(
    db: AsyncSession,
    *,
    workspace_id: int,
    year: int,
    week: int,
    summary: str,
    repeated_issues: list[str],
    next_time_notes: list[str],
    pr_count: int,
    learning_count: int,
) -> WeeklyDigest:
    digest = await db.scalar(
        select(WeeklyDigest).where(
            WeeklyDigest.workspace_id == workspace_id,
            WeeklyDigest.year == year,
            WeeklyDigest.week == week,
        )
    )
    if digest is not None:
        digest.summary = summary
        digest.repeated_issues = repeated_issues
        digest.next_time_notes = next_time_notes
        digest.pr_count = pr_count
        digest.learning_count = learning_count
        digest.visibility = "workspace_shared"
        return digest

    digest = WeeklyDigest(
        workspace_id=workspace_id,
        year=year,
        week=week,
        summary=summary,
        repeated_issues=repeated_issues,
        next_time_notes=next_time_notes,
        pr_count=pr_count,
        learning_count=learning_count,
        visibility="workspace_shared",
    )
    db.add(digest)
    await db.flush()
    return digest


async def seed_demo_data(
    db: AsyncSession,
    *,
    email: str = "demo@example.com",
    password: str = "demo12345",
    year: int | None = None,
    week: int | None = None,
) -> DemoSeedResult:
    now = datetime.now(timezone.utc)
    iso = now.isocalendar()
    target_year = year or iso.year
    target_week = week or iso.week

    user = await _get_or_create_user(db, email, password)
    workspace = await ensure_personal_workspace(db, user)
    await db.flush()

    repository_specs = [
        {
            "github_id": 91001,
            "full_name": "demo/pr-knowledge-hub-api",
            "name": "pr-knowledge-hub-api",
            "pr_number": 14,
            "title": "Tighten webhook processing and repository scoping",
            "body": "Improves workspace-aware repository resolution and processing safety.",
            "author": "demo-bot",
            "url": "https://github.com/demo/pr-knowledge-hub-api/pull/14",
            "merged_at": datetime(2026, 3, 24, 10, 0, tzinfo=timezone.utc),
            "items": [
                {
                    "title": "Filter repository data by workspace first",
                    "detail": "Queries that join pull requests and repositories should scope by workspace to avoid cross-tenant reads.",
                    "category": "security",
                    "confidence": 0.94,
                    "action": "Start list/detail queries from the workspace boundary, then join outward.",
                    "evidence": "Repository and learning item endpoints now enforce the active workspace before returning data.",
                    "visibility": "workspace_shared",
                },
                {
                    "title": "Keep webhook ingestion idempotent",
                    "detail": "Webhook retries are normal, so repository and PR upserts should tolerate repeated delivery without duplicating records.",
                    "category": "design",
                    "confidence": 0.89,
                    "action": "Use stable lookup keys like workspace + full_name and repository + PR number before insert.",
                    "evidence": "The processor already resolves repositories and PRs using GitHub identifiers and workspace scope.",
                    "visibility": "workspace_shared",
                },
            ],
        },
        {
            "github_id": 91002,
            "full_name": "demo/pr-knowledge-hub-web",
            "name": "pr-knowledge-hub-web",
            "pr_number": 21,
            "title": "Improve dashboard empty states and workspace context",
            "body": "Adds clearer page copy and uses the stored workspace context on the client.",
            "author": "demo-bot",
            "url": "https://github.com/demo/pr-knowledge-hub-web/pull/21",
            "merged_at": datetime(2026, 3, 25, 13, 30, tzinfo=timezone.utc),
            "items": [
                {
                    "title": "Persist active workspace on login",
                    "detail": "The first post-login experience is smoother when the default workspace is stored immediately.",
                    "category": "design",
                    "confidence": 0.91,
                    "action": "Write the returned default workspace id into both local storage and cookie-backed request context.",
                    "evidence": "The login page now stores `default_workspace_id` and the API client forwards it as `X-Workspace-Id`.",
                    "visibility": "workspace_shared",
                },
                {
                    "title": "Show evidence and next action together",
                    "detail": "Learning items are easier to reuse when the reason and the future action are visible in the same card.",
                    "category": "code_quality",
                    "confidence": 0.86,
                    "action": "Keep cards structured as issue, evidence, and next action instead of a flat summary blob.",
                    "evidence": "The home page and learning item list now render evidence and action blocks separately.",
                    "visibility": "workspace_shared",
                },
            ],
        },
    ]

    repositories: list[Repository] = []
    pull_requests: list[PullRequest] = []
    learning_items: list[LearningItem] = []

    for spec in repository_specs:
        repository = await _get_or_create_repository(
            db,
            workspace_id=workspace.id,
            github_id=spec["github_id"],
            full_name=spec["full_name"],
            name=spec["name"],
        )
        repositories.append(repository)

        pull_request = await _get_or_create_pull_request(
            db,
            repository_id=repository.id,
            github_pr_number=spec["pr_number"],
            title=spec["title"],
            body=spec["body"],
            author=spec["author"],
            github_url=spec["url"],
            merged_at=spec["merged_at"],
        )
        pull_requests.append(pull_request)

        for item_spec in spec["items"]:
            learning_items.append(
                await _get_or_create_learning_item(
                    db,
                    workspace_id=workspace.id,
                    pull_request_id=pull_request.id,
                    title=item_spec["title"],
                    detail=item_spec["detail"],
                    category=item_spec["category"],
                    confidence=item_spec["confidence"],
                    action_for_next_time=item_spec["action"],
                    evidence=item_spec["evidence"],
                    visibility=item_spec["visibility"],
                )
            )

    digest = await _get_or_create_digest(
        db,
        workspace_id=workspace.id,
        year=target_year,
        week=target_week,
        summary="Workspace-scoped reads, stable PR ingestion, and clearer learning cards are the strongest recurring improvements this week.",
        repeated_issues=[
            "Data access needs an explicit workspace boundary on every list and detail path.",
            "Review feedback becomes reusable only when evidence and next action are stored together.",
        ],
        next_time_notes=[
            "Add seed data whenever a new page is introduced so empty-state regressions are visible early.",
            "Keep webhook processing idempotent before expanding GitHub integration breadth.",
        ],
        pr_count=len(pull_requests),
        learning_count=len(learning_items),
    )

    await db.commit()

    return DemoSeedResult(
        email=email,
        password=password,
        workspace_id=workspace.id,
        repository_count=len(repositories),
        pull_request_count=len(pull_requests),
        learning_item_count=len(learning_items),
        digest_id=digest.id,
    )
