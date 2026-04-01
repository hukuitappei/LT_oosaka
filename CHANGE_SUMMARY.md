# 実施事項サマリ

このドキュメントは、直近の整理・修正・リファクタリングで実施した内容を簡潔にまとめたものです。

## UI と表示修正

- frontend 側の文字化けと壊れた JSX を修正
- learning items / weekly digests 周辺の共通文言を整理
- backend 側の prompt、コメント、docstring の文字化けを UTF-8 前提で修復
- dashboard / login / learning items / weekly digests の表示文言を英語ベースで統一

## アーキテクチャ整理

- LLM provider の選択を共通レイヤーに集約
- legacy フィールド `WeeklyDigest.user_id` を削除し、対応 migration を追加
- fixture ベースの `/analyze` を本番 FastAPI app から外し、dev-only の導線へ分離
- webhook 起点の重い処理を FastAPI `BackgroundTasks` ではなく Celery に統一
- webhook / Celery / PR 処理 / digest 生成に構造化ログを追加

## Router / Service 分離

- PR 再解析の lookup と enqueue orchestration を `api/app/services/pull_requests.py` へ移動
- weekly digest の一覧取得、単体取得、期間解決、生成 orchestration を `api/app/services/weekly_digests.py` へ移動
- workspace の membership lookup と member 更新処理を `api/app/services/workspaces.py` へ移動
- auth の session orchestration を `api/app/services/user_sessions.py` へ移動
- GitHub OAuth callback の完了処理を `api/app/services/github_oauth.py` へ移動
- GitHub connection の一覧 / 作成 / link / 削除処理を `api/app/services/github_connections.py` へ移動
- auth の response schema を router から分離して `api/app/schemas/auth.py` を追加
- workspace router に残っていた `db.get(...)` ベースの workspace lookup を service に集約

## テストと品質ゲート

- frontend CI に `npm run lint` を追加し、その後に `npm run build` を実行する構成へ変更
- frontend に Playwright ベースの最小 browser E2E を追加
- mock API server を使う browser E2E の起動導線を追加
- backend テストを責務ごとに分割
- webhook 契約テストを独立
- PR reanalyze の router/service テストを分離
- weekly digest の router/service テストを分離
- workspace の router/service テストを分離
- auth の router/service テストを分離
- learning item の status/filter/update 契約テストを追加
- GitHub connection の router/service テストを追加
- 境界整理に合わせて docs と decision record を都度更新

## Learning Item 活用

- `LearningItem.status` を追加し、`new` / `in_progress` / `applied` / `ignored` を管理可能にした
- learning item 一覧 API に search / repository / PR / category / status / pagination を追加
- `PATCH /learning-items/{id}` で status / visibility 更新を可能にした
- summary API に `status_counts` を追加し、dashboard と learning items 画面に反映した
- learning items 画面に filter UI と status 更新 UI を追加した

## 現在の検証状況

- backend: `pytest -q api` で `99 passed`
- frontend: `npm run lint`
- frontend: `npm run build`
- frontend: `npm run test:e2e`
- frontend CI: `npm run lint`、`npm run build`、browser E2E

## 現在の方針

- `workspace` を主な ownership boundary とする
- router は HTTP と認可・例外変換に寄せる
- service は query と orchestration を持つ
- 重い非同期処理は Celery に統一する
