import Link from "next/link"
import { api } from "@/lib/api"
import { getRequestContextHeaders } from "@/lib/request-context"

const CATEGORY_LABELS: Record<string, string> = {
  security: "セキュリティ",
  performance: "パフォーマンス",
  design: "設計",
  testing: "テスト",
  code_quality: "コード品質",
  other: "その他",
}

export default async function Home() {
  const requestHeaders = await getRequestContextHeaders()
  const [items, digests] = await Promise.all([
    api.getLearningItems({ headers: requestHeaders }),
    api.getWeeklyDigests({ headers: requestHeaders }),
  ])

  if (!items && !digests) {
    return (
      <main className="mx-auto min-h-screen max-w-4xl p-8">
        <h1 className="mb-1 text-3xl font-bold">PR Knowledge Hub</h1>
        <p className="mb-8 text-gray-500">レビューの知見を、次回の判断に使えるダッシュボードです。</p>
        <p className="py-8 text-center text-gray-500">
          データを取得できませんでした。ログイン状態と API 接続を確認してください。
        </p>
      </main>
    )
  }

  const latestDigest = digests?.[0] ?? null
  const latestItems = (items ?? []).slice(0, 3)

  const categoryCounts: Record<string, number> = {}
  for (const item of items ?? []) {
    categoryCounts[item.category] = (categoryCounts[item.category] ?? 0) + 1
  }
  const topCategories = Object.entries(categoryCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3)

  return (
    <main className="mx-auto min-h-screen max-w-6xl px-6 py-10">
      <section className="mb-8 overflow-hidden rounded-[2rem] border border-white/10 bg-white/5 p-8 shadow-2xl shadow-black/20 backdrop-blur">
        <div className="grid gap-8 lg:grid-cols-[1.4fr_0.8fr]">
          <div>
            <p className="mb-3 text-xs font-semibold uppercase tracking-[0.35em] text-amber-300">
              ダッシュボード
            </p>
            <h1 className="max-w-3xl text-4xl font-semibold leading-tight text-white md:text-5xl">
              PRレビューの指摘を、<br />
              次回の判断に使える学びへ変える
            </h1>
            <p className="mt-4 max-w-2xl text-base leading-7 text-stone-300">
              レビューコメントを整理して、学びを実装や設計の改善に落とし込みます。
              週次ダイジェストでは、その週に増えた学びを振り返れます。
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <Link
                href="/learning-items"
                className="rounded-full bg-amber-300 px-5 py-3 text-sm font-medium text-stone-950 transition-transform hover:-translate-y-0.5"
              >
                学びを見る
              </Link>
              <Link
                href="/weekly-digests"
                className="rounded-full border border-white/15 px-5 py-3 text-sm font-medium text-white transition-colors hover:bg-white/10"
              >
                週次ダイジェストを見る
              </Link>
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-3 lg:grid-cols-1">
            <StatCard label="学びの件数" value={items?.length ?? 0} />
            <StatCard label="最新ダイジェストの学び数" value={latestDigest?.learning_count ?? 0} />
            <StatCard label="ダイジェスト件数" value={digests?.length ?? 0} />
          </div>
        </div>
      </section>

      <section className="mb-8 grid gap-4 md:grid-cols-3">
        <InsightCard
          title="学びの活用"
          body="レビューで見つかった課題を PR ごとに整理し、次の実装で使える形にします。"
        />
        <InsightCard
          title="次回につなげる"
          body="学びは根拠と次回アクションに分けて保存し、再発防止と共有をしやすくします。"
        />
        <InsightCard
          title="傾向を読む"
          body="カテゴリごとの件数を見て、今どこで学びが多いかを週次ダイジェストで把握できます。"
        />
      </section>

      <div className="grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
        <section className="rounded-[1.5rem] border border-white/10 bg-white/5 p-6 backdrop-blur">
          <div className="mb-5 flex items-center justify-between">
            <div>
              <h2 className="text-xl font-semibold text-white">最新の学び</h2>
              <p className="text-sm text-stone-400">レビューから抽出された直近のアクションです。</p>
            </div>
            <Link href="/learning-items" className="text-sm text-amber-300 hover:text-amber-200">
              すべて見る
            </Link>
          </div>

          {!latestItems.length ? (
            <p className="text-sm text-stone-400">まだ学びはありません。</p>
          ) : (
            <div className="space-y-4">
              {latestItems.map((item) => (
                <article key={item.id} className="rounded-2xl border border-white/10 bg-black/10 p-5">
                  <div className="mb-2 flex items-center justify-between gap-3">
                    <h3 className="font-medium text-white">{item.title}</h3>
                    <span className="rounded-full bg-white/10 px-3 py-1 text-xs text-stone-300">
                      {CATEGORY_LABELS[item.category] ?? item.category}
                    </span>
                  </div>
                  <p className="mb-3 text-xs uppercase tracking-[0.2em] text-stone-500">
                    {item.repository.full_name} / PR #{item.pull_request.github_pr_number}
                  </p>
                  <p className="mb-3 text-sm leading-6 text-stone-300">{item.detail}</p>
                  <div className="mb-3 rounded-2xl border border-amber-300/15 bg-amber-300/10 p-3">
                    <p className="mb-1 text-[11px] uppercase tracking-[0.22em] text-amber-200/80">根拠</p>
                    <p className="text-sm text-stone-200">{item.evidence}</p>
                  </div>
                  <div className="rounded-2xl border border-sky-300/15 bg-sky-300/10 p-3">
                    <p className="mb-1 text-[11px] uppercase tracking-[0.22em] text-sky-200/80">次回アクション</p>
                    <p className="text-sm text-stone-100">{item.action_for_next_time}</p>
                  </div>
                  <a
                    href={item.pull_request.github_url}
                    target="_blank"
                    rel="noreferrer"
                    className="mt-3 inline-block text-sm text-sky-300 hover:text-sky-200"
                  >
                    GitHub の PR を開く
                  </a>
                </article>
              ))}
            </div>
          )}
        </section>

        <div className="space-y-6">
          {latestDigest && (
            <section className="rounded-[1.5rem] border border-white/10 bg-white/5 p-6 backdrop-blur">
              <div className="mb-3 flex items-start justify-between gap-3">
                <div>
                  <h2 className="text-xl font-semibold text-white">最新の週次ダイジェスト</h2>
                  <p className="text-sm text-stone-400">
                    {latestDigest.year}年 第{latestDigest.week}週
                  </p>
                </div>
                <span className="rounded-full bg-white/10 px-3 py-1 text-xs text-stone-300">
                  {latestDigest.learning_count}件
                </span>
              </div>
              <p className="mb-4 text-sm leading-6 text-stone-300">{latestDigest.summary}</p>
              <Link
                href={`/weekly-digests/${latestDigest.id}`}
                className="text-sm text-amber-300 hover:text-amber-200"
              >
                ダイジェストの詳細を見る
              </Link>
            </section>
          )}

          <section className="rounded-[1.5rem] border border-white/10 bg-white/5 p-6 backdrop-blur">
            <h2 className="mb-4 text-xl font-semibold text-white">よく出るカテゴリ</h2>
            {topCategories.length > 0 ? (
              <div className="space-y-3">
                {topCategories.map(([cat, count]) => (
                  <div key={cat} className="rounded-2xl border border-white/10 bg-black/10 p-4">
                    <div className="mb-2 flex items-center justify-between text-sm">
                      <span className="text-stone-200">{CATEGORY_LABELS[cat] ?? cat}</span>
                      <span className="font-mono text-stone-400">{count}</span>
                    </div>
                    <div className="h-2 rounded-full bg-white/10">
                      <div
                        className="h-2 rounded-full bg-gradient-to-r from-amber-300 to-sky-400"
                        style={{ width: `${Math.min(100, (count / (items?.length ?? 1)) * 100)}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-stone-400">まだカテゴリ別の学びはありません。</p>
            )}
          </section>
        </div>
      </div>
    </main>
  )
}

function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-[1.5rem] border border-white/10 bg-black/20 p-5">
      <p className="mb-1 text-sm text-stone-400">{label}</p>
      <p className="text-3xl font-semibold text-white">{value}</p>
    </div>
  )
}

function InsightCard({ title, body }: { title: string; body: string }) {
  return (
    <section className="rounded-[1.5rem] border border-white/10 bg-white/5 p-5 backdrop-blur">
      <p className="mb-2 text-sm font-medium text-amber-300">{title}</p>
      <p className="text-sm leading-6 text-stone-300">{body}</p>
    </section>
  )
}
