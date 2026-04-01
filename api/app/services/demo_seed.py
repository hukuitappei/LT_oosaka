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


async def _sync_learning_items_for_pull_request(
    db: AsyncSession,
    *,
    workspace_id: int,
    pull_request_id: int,
    items: list[dict[str, str | float]],
) -> list[LearningItem]:
    existing = list(
        (
            await db.execute(
                select(LearningItem)
                .where(
                    LearningItem.workspace_id == workspace_id,
                    LearningItem.pull_request_id == pull_request_id,
                )
                .order_by(LearningItem.id.asc())
            )
        )
        .scalars()
        .all()
    )

    synced: list[LearningItem] = []
    for item_model, item_spec in zip(existing, items):
        item_model.title = str(item_spec["title"])
        item_model.detail = str(item_spec["detail"])
        item_model.category = str(item_spec["category"])
        item_model.confidence = float(item_spec["confidence"])
        item_model.action_for_next_time = str(item_spec["action"])
        item_model.evidence = str(item_spec["evidence"])
        item_model.visibility = str(item_spec["visibility"])
        synced.append(item_model)

    for item_spec in items[len(existing):]:
        item_model = LearningItem(
            workspace_id=workspace_id,
            pull_request_id=pull_request_id,
            schema_version="1.0",
            title=str(item_spec["title"]),
            detail=str(item_spec["detail"]),
            category=str(item_spec["category"]),
            confidence=float(item_spec["confidence"]),
            action_for_next_time=str(item_spec["action"]),
            evidence=str(item_spec["evidence"]),
            visibility=str(item_spec["visibility"]),
        )
        db.add(item_model)
        await db.flush()
        synced.append(item_model)

    for extra in existing[len(items):]:
        await db.delete(extra)

    return synced


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
            "title": "Webhook 処理とリポジトリ境界を強化する",
            "body": "ワークスペース単位で安全にリポジトリを解決し、Webhook 処理を安定させる変更。",
            "author": "demo-bot",
            "url": "https://github.com/demo/pr-knowledge-hub-api/pull/14",
            "merged_at": datetime(2026, 3, 24, 10, 0, tzinfo=timezone.utc),
            "items": [
                {
                    "title": "リポジトリ関連データは先にワークスペースで絞り込む",
                    "detail": "PR とリポジトリを結合するクエリは、最初にワークスペース境界で絞り込まないと他テナントの情報を混ぜる危険がある。",
                    "category": "security",
                    "confidence": 0.94,
                    "action": "一覧や詳細の取得は、ワークスペース条件を起点にしてから関連テーブルを結合する。",
                    "evidence": "リポジトリ API と学び API は、レスポンスを返す前にアクティブなワークスペースで必ず絞り込むようになった。",
                    "visibility": "workspace_shared",
                },
                {
                    "title": "Webhook 取り込みは冪等に保つ",
                    "detail": "Webhook は再送される前提なので、リポジトリや PR の upsert は同じイベントが複数回来ても重複登録しない設計にする必要がある。",
                    "category": "design",
                    "confidence": 0.89,
                    "action": "登録前に、workspace + full_name や repository + PR 番号のような安定キーで既存データを確認する。",
                    "evidence": "現在のプロセッサは、GitHub ID とワークスペース情報を使ってリポジトリと PR を解決している。",
                    "visibility": "workspace_shared",
                },
            ],
        },
        {
            "github_id": 91002,
            "full_name": "demo/pr-knowledge-hub-web",
            "name": "pr-knowledge-hub-web",
            "pr_number": 21,
            "title": "ダッシュボードの空状態とワークスペース文脈を改善する",
            "body": "ページ文言を整理し、クライアント側で保持したワークスペース文脈を使う変更。",
            "author": "demo-bot",
            "url": "https://github.com/demo/pr-knowledge-hub-web/pull/21",
            "merged_at": datetime(2026, 3, 25, 13, 30, tzinfo=timezone.utc),
            "items": [
                {
                    "title": "ログイン時にアクティブなワークスペースを保持する",
                    "detail": "ログイン直後に既定ワークスペースを保存しておくと、最初の画面遷移から正しい文脈でデータを表示できる。",
                    "category": "design",
                    "confidence": 0.91,
                    "action": "返ってきた default_workspace_id を localStorage と Cookie の両方に保存して、以後の API 呼び出しで送る。",
                    "evidence": "ログイン画面は `default_workspace_id` を保存し、API クライアントは `X-Workspace-Id` として送るようになっている。",
                    "visibility": "workspace_shared",
                },
                {
                    "title": "根拠と次回アクションを同じカードで見せる",
                    "detail": "学びは、なぜそう言えるのかと次に何をするのかが同じ場所で見えた方が再利用しやすい。",
                    "category": "code_quality",
                    "confidence": 0.86,
                    "action": "カードは単なる要約文ではなく、論点・根拠・次回アクションの構造を保って表示する。",
                    "evidence": "ホーム画面と学び一覧では、根拠と次回アクションを別ブロックで表示している。",
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

        learning_items.extend(
            await _sync_learning_items_for_pull_request(
                db,
                workspace_id=workspace.id,
                pull_request_id=pull_request.id,
                items=spec["items"],
            )
        )

    digest = await _get_or_create_digest(
        db,
        workspace_id=workspace.id,
        year=target_year,
        week=target_week,
        summary="今週は、ワークスペース境界を守る取得処理、冪等な PR 取り込み、そして学びカードの見せ方の改善が大きな前進だった。",
        repeated_issues=[
            "一覧と詳細の両方で、常にワークスペース境界を明示しないとデータの混在が起きやすい。",
            "レビュー指摘は、根拠と次回アクションをセットで残さないと再利用しにくい。",
        ],
        next_time_notes=[
            "新しい画面を追加したら、空状態だけでなくデモデータも先に用意して見え方を確認する。",
            "GitHub 連携の対象を広げる前に、Webhook 処理の冪等性を崩さないことを優先する。",
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
