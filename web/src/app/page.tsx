import Link from "next/link"
import { api } from "@/lib/api"
import { getRequestContextHeaders } from "@/lib/request-context"

const CATEGORY_LABELS: Record<string, string> = {
  security: "Security",
  performance: "Performance",
  design: "Design",
  testing: "Testing",
  code_quality: "Code quality",
  other: "Other",
}

export default async function Home() {
  const requestHeaders = await getRequestContextHeaders()
  const [items, digests, learningSummary] = await Promise.all([
    api.getLearningItems({ headers: requestHeaders }),
    api.getWeeklyDigests({ headers: requestHeaders }),
    api.getLearningItemsSummary({ headers: requestHeaders }),
  ])

  if (!items && !digests && !learningSummary) {
    return (
      <main className="mx-auto min-h-screen max-w-4xl p-8">
        <h1 className="mb-2 text-3xl font-bold text-white">PR Knowledge Hub</h1>
        <p className="text-stone-400">
          API に接続できないため、ダッシュボードを表示できませんでした。
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

  const topCategories =
    learningSummary?.top_categories.length
      ? learningSummary.top_categories.map(({ category, count }) => [category, count] as const)
      : Object.entries(categoryCounts)
          .sort((a, b) => b[1] - a[1])
          .slice(0, 3)

  return (
    <main className="mx-auto min-h-screen max-w-6xl px-6 py-10">
      <section className="mb-8 overflow-hidden rounded-[2rem] border border-white/10 bg-white/5 p-8 shadow-2xl shadow-black/20 backdrop-blur">
        <div className="grid gap-8 lg:grid-cols-[1.4fr_0.8fr]">
          <div>
            <p className="mb-3 text-xs font-semibold uppercase tracking-[0.35em] text-amber-300">
              Learning Dashboard
            </p>
            <h1 className="max-w-3xl text-4xl font-semibold leading-tight text-white md:text-5xl">
              PRレビューの学びを
              <br />
              毎週たまる知識として追えるようにする
            </h1>
            <p className="mt-4 max-w-2xl text-base leading-7 text-stone-300">
              学びカード、週次ダイジェスト、カテゴリ傾向をまとめて確認できます。追加した週次トレンドで、
              直近 8 週間の積み上がりも一目で追えます。
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
                週次ダイジェスト
              </Link>
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-1">
            <StatCard label="総学び件数" value={learningSummary?.total_learning_items ?? items?.length ?? 0} />
            <StatCard label="今週の学び" value={learningSummary?.current_week_count ?? 0} />
            <StatCard label="最新ダイジェストの学び" value={latestDigest?.learning_count ?? 0} />
            <StatCard label="ダイジェスト数" value={digests?.length ?? 0} />
          </div>
        </div>
      </section>

      <section className="mb-8 grid gap-4 md:grid-cols-3">
        <InsightCard
          title="継続的に残す"
          body="レビューで得た指摘を、その場限りで終わらせずワークスペースの知識として蓄積します。"
        />
        <InsightCard
          title="次回の行動につなげる"
          body="学びには evidence と next action が残るので、次の PR で試す改善にそのままつなげられます。"
        />
        <InsightCard
          title="偏りを見つける"
          body="カテゴリ分布と週次推移を並べて見ることで、繰り返し出ている弱点を見つけやすくします。"
        />
      </section>

      <div className="grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
        <section className="rounded-[1.5rem] border border-white/10 bg-white/5 p-6 backdrop-blur">
          <div className="mb-5 flex items-center justify-between">
            <div>
              <h2 className="text-xl font-semibold text-white">最新の学び</h2>
              <p className="text-sm text-stone-400">最近追加された learning item</p>
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
                    <p className="mb-1 text-[11px] uppercase tracking-[0.22em] text-amber-200/80">Evidence</p>
                    <p className="text-sm text-stone-200">{item.evidence}</p>
                  </div>
                  <div className="rounded-2xl border border-sky-300/15 bg-sky-300/10 p-3">
                    <p className="mb-1 text-[11px] uppercase tracking-[0.22em] text-sky-200/80">Next action</p>
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
          <section className="rounded-[1.5rem] border border-white/10 bg-white/5 p-6 backdrop-blur">
            <div className="mb-4 flex items-center justify-between gap-3">
              <div>
                <h2 className="text-xl font-semibold text-white">Learning Trend</h2>
                <p className="text-sm text-stone-400">Last 8 weeks</p>
              </div>
              <span className="rounded-full bg-white/10 px-3 py-1 text-xs text-stone-300">
                this week {learningSummary?.current_week_count ?? 0}
              </span>
            </div>
            <LearningTrendChart points={learningSummary?.weekly_points ?? []} />
          </section>

          {latestDigest && (
            <section className="rounded-[1.5rem] border border-white/10 bg-white/5 p-6 backdrop-blur">
              <div className="mb-3 flex items-start justify-between gap-3">
                <div>
                  <h2 className="text-xl font-semibold text-white">最新の週次ダイジェスト</h2>
                  <p className="text-sm text-stone-400">
                    {latestDigest.year} / W{latestDigest.week}
                  </p>
                </div>
                <span className="rounded-full bg-white/10 px-3 py-1 text-xs text-stone-300">
                  {latestDigest.learning_count} 件
                </span>
              </div>
              <p className="mb-4 text-sm leading-6 text-stone-300">{latestDigest.summary}</p>
              <Link
                href={`/weekly-digests/${latestDigest.id}`}
                className="text-sm text-amber-300 hover:text-amber-200"
              >
                ダイジェスト詳細を見る
              </Link>
            </section>
          )}

          <section className="rounded-[1.5rem] border border-white/10 bg-white/5 p-6 backdrop-blur">
            <h2 className="mb-4 text-xl font-semibold text-white">Top Categories</h2>
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
                        style={{
                          width: `${Math.min(
                            100,
                            (count / Math.max(learningSummary?.total_learning_items ?? items?.length ?? 1, 1)) * 100,
                          )}%`,
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-stone-400">カテゴリ傾向はまだありません。</p>
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

function LearningTrendChart({
  points,
}: {
  points: Array<{ label: string; learning_count: number }>
}) {
  if (!points.length) {
    return <p className="text-sm text-stone-400">No trend data yet.</p>
  }

  const maxCount = Math.max(...points.map((point) => point.learning_count), 1)

  return (
    <div className="space-y-4">
      <div className="grid h-48 grid-cols-8 items-end gap-3">
        {points.map((point) => {
          const height = Math.max(12, Math.round((point.learning_count / maxCount) * 100))
          return (
            <div key={point.label} className="flex h-full flex-col justify-end gap-2">
              <div className="flex-1 rounded-t-[1rem] bg-white/5 p-1">
                <div
                  className="w-full rounded-[0.85rem] bg-gradient-to-t from-amber-300 via-orange-300 to-sky-400"
                  style={{ height: `${height}%` }}
                />
              </div>
              <div className="text-center">
                <p className="font-mono text-xs text-stone-200">{point.learning_count}</p>
                <p className="text-[10px] text-stone-500">{point.label.slice(5)}</p>
              </div>
            </div>
          )
        })}
      </div>
      <p className="text-sm leading-6 text-stone-400">
        週ごとの学び件数を同じ軸で追えるので、積み上がりと停滞がすぐに分かります。
      </p>
    </div>
  )
}
