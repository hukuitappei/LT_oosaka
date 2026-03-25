# 試行錯誤を知識に変える週報AI 実装計画案

## 目的
AIに実装を任せる時代に、完成コードだけでなく、途中で発生した詰まり、失敗、判断の履歴を知識として残せる仕組みを作る。  
MVPでは GitHub PR を入力にして、レビューコメントと修正履歴から「今週の学び」を週報形式で生成する。

---

## ゴール

### MVPで実現すること
- 個人用ツールとして、自分のリポジトリ群を対象に使える
- GitHub App を1リポジトリにインストールできる
- PRとレビューコメントを取得できる
- PR単位で学びを構造化抽出できる
- 週単位で学びを集約し、週報を生成できる
- 過去の学びを一覧で見返せる

### 今回やらないこと
- チーム横断のナレッジ共有
- Slack連携
- Issue / commit / ローカルログの統合
- 自動分類の高度化
- 評価スコアリング
- マルチテナント前提の認証設計

---

## 想定技術スタック

### フロントエンド
- Next.js
- TypeScript
- App Router

### バックエンド
- FastAPI
- Python 3.13
- Pydantic
- SQLAlchemy

### データ / 非同期処理
- PostgreSQL
- Redis
- Celery

### 外部連携
- GitHub App
- GitHub Webhooks

### LLM
- 第一候補: Ollama
- 代替候補: クラウドLLM API

### インフラ
- Docker
- docker compose

---

## 技術選定の意図

### Next.js
- 継続利用前提のUIを作りやすい
- 個人用ダッシュボード、一覧、詳細、検索を育てやすい

### FastAPI
- API中心の構成にしやすい
- 型付きの入出力定義と非同期処理の分離がしやすい

### PostgreSQL
- 学び、PR、レビューコメント、週報を正規化して保存できる
- JSONB や全文検索による拡張も取りやすい

### Redis + Celery
- PR解析や週報生成を非同期ジョブに逃がせる
- Webhook受信と重いLLM処理を分離できる

### GitHub App
- 個人トークンより権限管理が明確
- Webhookを自然に使える

### Ollama
- ローカルLLMで運用コストを抑えられる
- 将来、クラウドLLMへのフォールバックも設計可能

---

## システム構成

### 全体像
1. GitHub App が PR イベントを受信する
2. FastAPI が webhook を受けてジョブを登録する
3. Celery worker が GitHub API から PR 情報を取得する
4. 前処理でレビューコメントと修正履歴を整形する
5. LLM が学びを構造化 JSON で返す
6. FastAPI がバリデーション後に PostgreSQL へ保存する
7. Next.js が週報一覧、学び一覧、詳細を表示する

### コンポーネント
- `web`: Next.js
- `api`: FastAPI
- `worker`: Celery
- `db`: PostgreSQL
- `cache`: Redis
- `llm`: Ollama

---

## 利用者と認証方針

### 初期前提
- 最初は自分専用の個人ツールとして作る
- 利用者は1人を前提にする
- 対象は自分がインストールした GitHub App 配下のリポジトリ

### この前提での設計
- アプリ内のユーザー管理は持たない
- Web画面はローカル利用または限定公開を前提にする
- 認証は Phase 1 では省略可能
- 必要なら最小限のアクセス制限だけ後付けする

### 将来拡張
- 他者利用を考える段階で初めて認証を正式導入する
- その時点で GitHub OAuth または同等のログイン基盤を検討する
- その前にマルチテナント前提の API / DB 設計へ広げない

---

## MVPのユーザーフロー

### MVP-0: 最小検証
1. サンプルPRデータを手動で投入する
2. レビューコメントと修正履歴を前処理する
3. `learning_items` を構造化抽出する
4. 出力の質を人間がレビューする

### MVP-0 の目的
- GitHub App や webhook より前に、学び抽出の中核価値を検証する
- `PRから再利用可能な学びが本当に取れるか` を先に見る
- 前処理と出力スキーマの妥当性を固める

### MVP-0 の完了条件
- 1つのPRから `learning_items` を安定して出力できる
- evidence と結びついた学びが出ている
- 単なる要約ではなく、次回の行動に変換されている
- 人間が見て「再利用したい」と思える粒度になっている

### 初回セットアップ
1. ユーザーが GitHub App を対象リポジトリにインストールする
2. アプリが対象リポジトリを認識する

### データ取り込み
1. PR作成またはレビュー更新で webhook 発火
2. PR情報取得ジョブを投入
3. PR本文、レビューコメント、修正履歴を取得

### 学び抽出
1. 前処理でノイズを除去
2. LLMに構造化出力を要求
3. `learning_items` と `next_time_notes` を保存

### 週報生成
1. 指定週の `learning_items` を集約
2. 重複や類似をまとめる
3. 週報として要約を生成
4. UIで表示する

---

## データモデル案

### 基本テーブル
- `repositories`
- `pull_requests`
- `review_comments`
- `review_threads`
- `learning_items`
- `weekly_digests`
- `processing_jobs`

### 学びデータの考え方
- PRやレビューコメントは生データとして保持する
- LLM出力は保存前に正規化する
- 週報は生成結果をキャッシュして再利用する

---

## LLM出力フォーマット方針

### 基本方針
- JSON only
- `schema_version` を必須にする
- バージョンごとに Pydantic で検証する
- DBモデルとは分離する

### v1で扱う項目
- `schema_version`
- `source`
- `summary`
- `learning_items`
- `repeated_issues`
- `next_time_notes`

### learning_item の基本項目
- `title`
- `detail`
- `category`
- `confidence`
- `action_for_next_time`
- `evidence`

### 運用方針
- 必須項目は少なく始める
- optional フィールドで拡張する
- 破壊的変更だけメジャーバージョンを上げる

---

## APIの初期案

### GitHub連携
- `POST /webhooks/github`
- `GET /repositories`
- `GET /repositories/{id}/pull-requests`

### 学び閲覧
- `GET /learning-items`
- `GET /learning-items/{id}`
- `GET /weekly-digests`
- `GET /weekly-digests/{id}`

### 再処理
- `POST /pull-requests/{id}/reanalyze`
- `POST /weekly-digests/generate`

### 認証について
- 初期段階では認証必須APIを置かない
- 個人利用前提で、実行環境のネットワーク境界で守る
- 公開利用に広げる段階で認証付きAPIへ移行する

---

## GitHub App 権限案
- Metadata: read
- Pull requests: read
- Contents: read

### 受ける webhook
- `pull_request`
- `pull_request_review`
- `pull_request_review_comment`

---

## 画面案

### 1. ダッシュボード
- 今週の学び件数
- よく出る詰まりカテゴリ
- 最新週報への導線

### 2. 週報一覧
- 週ごとの digest 一覧
- サマリーと学び件数

### 3. 週報詳細
- 今週の学び
- 繰り返している詰まり
- 次回の自分へのメモ

### 4. PR詳細
- PR概要
- レビューコメント
- 抽出された学び
- 根拠となる evidence

---

## 実装フェーズ

### Phase 1: 基盤構築
- monorepo 作成
- Next.js / FastAPI / PostgreSQL / Redis / Celery / Ollama の compose 構成
- ヘルスチェックと疎通確認

### Phase 2: MVP-0 の検証
- サンプルPRデータを固定する
- コメント正規化と evidence 生成を実装する
- LLM出力スキーマを固定する
- `learning_items` の品質を確認する

### Phase 3: GitHub取り込み
- GitHub App 作成
- webhook 受信
- PR / コメント取得
- DB保存

### Phase 4: 学び抽出の本接続
- LLM provider 抽象化
- JSON schema + Pydantic バリデーション実装
- GitHub取得データを learning_items に変換して保存

### Phase 5: 週報生成
- 週単位集約
- digest 生成
- UI実装

### Phase 6: 任意の拡張
- 学び一覧の検索
- 再分析導線
- provider 切替

### Phase 6 に入る条件
- Phase 5 までで個人ツールとして日常利用できる
- `learning_items` の品質に手応えがある
- 週報が実際に振り返りで使える
- そのうえで検索性や provider 比較が必要になった場合だけ着手する

---

## ディレクトリ構成案

```text
/
  web/
  api/
  worker/
  infra/
  docs/
  docker-compose.yml
```

### web
- Next.js UI

### api
- FastAPI
- GitHub連携
- DBアクセス
- LLM呼び出し

### worker
- Celery task
- 集約処理
- 再分析処理

### infra
- Docker関連
- 環境変数テンプレート

---

## リスク

### ローカルLLMの品質
- 長いPRで精度が落ちる可能性がある
- 対策: 前処理で入力を圧縮し、provider 抽象化を入れる

### データ量とノイズ
- コメントがそのままでは学びにならないケースがある
- 対策: evidence を残しつつ、前処理で指摘の粒度を整える

### Webhook起点の複雑さ
- 同一PRに複数イベントが飛ぶ
- 対策: `processing_jobs` と idempotency を設計する

---

## MVP完了条件
- 個人用ツールとして継続利用できる状態になっている
- 1つのリポジトリで GitHub App が動く
- 1つのPRから学び3件以上を安定して抽出できる
- 抽出された学びが evidence に結びついている
- 抽出された学びが次回の行動に変換されている
- 抽出結果が単なる要約ではなく、再利用可能な粒度になっている
- 1週間分のPRから週報を生成できる
- UIで過去の学びを見返せる

---

## ひとことで言うと
PRレビューで終わっていた指摘を、次回の自分に再利用できる知識へ変えるための、週報生成システムを作る。
