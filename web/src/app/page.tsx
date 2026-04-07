import Link from "next/link"
import { api } from "@/lib/api"
import { CATEGORY_LABELS, LEARNING_STATUS_LABELS } from "@/lib/learning-item-labels"
import { getRequestContextHeaders } from "@/lib/request-context"

export default async function Home() {
  const requestHeaders = await getRequestContextHeaders()
  const [items, digests, learningSummary, profile, currentSpace] = await Promise.all([
    api.getLearningItems({ headers: requestHeaders, query: { limit: 3 } }),
    api.getWeeklyDigests({ headers: requestHeaders }),
    api.getLearningItemsSummary({ headers: requestHeaders }),
    api.getCurrentUserProfile({ headers: requestHeaders }),
    api.getCurrentSpace({ headers: requestHeaders }),
  ])
  const spaceSettings = currentSpace
    ? await api.getSpaceSettings(currentSpace.id, { headers: requestHeaders })
    : null

  if (!items && !digests && !learningSummary && !currentSpace) {
    return (
      <main className="mx-auto min-h-screen max-w-4xl px-6 py-10">
        <h1 className="mb-3 text-3xl font-semibold text-white">PR Knowledge Hub</h1>
        <p className="text-stone-400">The API is unavailable right now. Try again after the backend starts.</p>
      </main>
    )
  }

  const latestDigest = digests?.[0] ?? null
  const latestItems = items ?? []
  const focusLabels = spaceSettings?.active_focus_labels ?? []
  const repeatedIssues = latestDigest?.repeated_issues ?? []
  const nextActions = latestDigest?.next_time_notes ?? []
  const statusCounts = Object.fromEntries(
    (learningSummary?.status_counts ?? []).map((row) => [row.status, row.count]),
  )

  return (
    <main className="mx-auto min-h-screen max-w-6xl px-6 py-10">
      <section className="mb-8 overflow-hidden rounded-[2rem] border border-white/10 bg-white/5 p-8 shadow-2xl shadow-black/20 backdrop-blur">
        <div className="grid gap-8 lg:grid-cols-[1.4fr_0.8fr]">
          <div>
            <p className="mb-3 text-xs font-semibold uppercase tracking-[0.35em] text-amber-300">
              Improvement Hub
            </p>
            <h1 className="max-w-3xl text-4xl font-semibold leading-tight text-white md:text-5xl">
              Keep one space focused
              <br />
              on the next team improvement.
            </h1>
            <p className="mt-4 max-w-2xl text-base leading-7 text-stone-300">
              Pull requests, repeated issues, active goals, and weekly review stay connected so the
              team can move from feedback to repeatable change.
            </p>
            <div className="mt-5 flex flex-wrap gap-3 text-sm text-stone-300">
              <Pill label="Current Space" value={spaceSettings?.display_name ?? currentSpace?.name ?? "Personal Space"} />
              <Pill label="Spaces" value={String(profile?.spaces.length ?? 0)} />
              <Pill label="Default Visibility" value={spaceSettings?.default_visibility ?? "workspace_shared"} />
            </div>
            <div className="mt-6 flex flex-wrap gap-3">
              <Link
                href="/learning-items"
                className="rounded-full bg-amber-300 px-5 py-3 text-sm font-medium text-stone-950 transition-transform hover:-translate-y-0.5"
              >
                Learning Items
              </Link>
              <Link
                href="/weekly-digests"
                className="rounded-full border border-white/15 px-5 py-3 text-sm font-medium text-white transition-colors hover:bg-white/10"
              >
                Weekly Digests
              </Link>
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-1">
            <StatCard label="Total Items" value={learningSummary?.total_learning_items ?? 0} />
            <StatCard label="New" value={statusCounts.new ?? 0} />
            <StatCard label="In Progress" value={statusCounts.in_progress ?? 0} />
            <StatCard label="Digests" value={digests?.length ?? 0} />
          </div>
        </div>
      </section>

      <div className="grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
        <section className="rounded-[1.5rem] border border-white/10 bg-white/5 p-6 backdrop-blur">
          <div className="mb-5 flex items-center justify-between">
            <div>
              <h2 className="text-xl font-semibold text-white">Latest Learning Items</h2>
              <p className="text-sm text-stone-400">Recent review signals inside the current space</p>
            </div>
            <Link href="/learning-items" className="text-sm text-amber-300 hover:text-amber-200">
              View all
            </Link>
          </div>

          {!latestItems.length ? (
            <p className="text-sm text-stone-400">No learning items yet.</p>
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
                  <div className="flex items-center justify-between text-sm text-stone-300">
                    <span>{LEARNING_STATUS_LABELS[item.status]}</span>
                    <div className="flex items-center gap-3">
                      <Link href={`/pull-requests/${item.pull_request.id}`} className="text-amber-300 hover:text-amber-200">
                        Review insights
                      </Link>
                      <a
                        href={item.pull_request.github_url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-sky-300 hover:text-sky-200"
                      >
                        Open PR
                      </a>
                    </div>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>

        <div className="space-y-6">
          <section className="rounded-[1.5rem] border border-white/10 bg-white/5 p-6 backdrop-blur">
            <h2 className="mb-4 text-xl font-semibold text-white">Active Goal</h2>
            <div className="rounded-2xl border border-white/10 bg-black/10 p-4">
              <p className="text-sm leading-6 text-stone-300">
                {spaceSettings?.active_goal ?? "No active goal yet. Add one in space settings to guide the next cycle."}
              </p>
            </div>
            {focusLabels.length ? (
              <div className="mt-4 flex flex-wrap gap-2">
                {focusLabels.map((label) => (
                  <span key={label} className="rounded-full bg-white/10 px-3 py-1 text-xs text-stone-200">
                    {label}
                  </span>
                ))}
              </div>
            ) : null}
          </section>

          {latestDigest ? (
            <section className="rounded-[1.5rem] border border-white/10 bg-white/5 p-6 backdrop-blur">
              <div className="mb-3 flex items-start justify-between gap-3">
                <div>
                  <h2 className="text-xl font-semibold text-white">Latest Weekly Digest</h2>
                  <p className="text-sm text-stone-400">
                    {latestDigest.year} / W{latestDigest.week}
                  </p>
                </div>
                <span className="rounded-full bg-white/10 px-3 py-1 text-xs text-stone-300">
                  {latestDigest.learning_count} items
                </span>
              </div>
              <p className="mb-4 text-sm leading-6 text-stone-300">{latestDigest.summary}</p>
              <Link
                href={`/weekly-digests/${latestDigest.id}`}
                className="text-sm text-amber-300 hover:text-amber-200"
              >
                Open digest
              </Link>
            </section>
          ) : null}

          <section className="rounded-[1.5rem] border border-white/10 bg-white/5 p-6 backdrop-blur">
            <h2 className="mb-4 text-xl font-semibold text-white">Repeated Issues</h2>
            {repeatedIssues.length ? (
              <div className="space-y-3">
                {repeatedIssues.map((issue) => (
                  <div key={issue} className="rounded-2xl border border-white/10 bg-black/10 p-4">
                    <p className="text-sm text-stone-200">{issue}</p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-stone-400">No repeated issues highlighted yet.</p>
            )}
          </section>

          <section className="rounded-[1.5rem] border border-white/10 bg-white/5 p-6 backdrop-blur">
            <h2 className="mb-4 text-xl font-semibold text-white">Next Actions</h2>
            {nextActions.length ? (
              <div className="space-y-3">
                {nextActions.map((action) => (
                  <div key={action} className="rounded-2xl border border-white/10 bg-black/10 p-4">
                    <p className="text-sm text-stone-200">{action}</p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-stone-400">No next actions captured yet.</p>
            )}
          </section>

          <section className="rounded-[1.5rem] border border-white/10 bg-white/5 p-6 backdrop-blur">
            <h2 className="mb-4 text-xl font-semibold text-white">Status Snapshot</h2>
            <div className="space-y-3">
              {["new", "in_progress", "applied", "ignored"].map((status) => (
                <div key={status} className="rounded-2xl border border-white/10 bg-black/10 p-4">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-stone-200">
                      {LEARNING_STATUS_LABELS[status]}
                    </span>
                    <span className="font-mono text-stone-400">{statusCounts[status] ?? 0}</span>
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section className="rounded-[1.5rem] border border-white/10 bg-white/5 p-6 backdrop-blur">
            <h2 className="mb-4 text-xl font-semibold text-white">Top Categories</h2>
            {(learningSummary?.top_categories ?? []).length ? (
              <div className="space-y-3">
                {learningSummary?.top_categories.map(({ category, count }) => (
                  <div key={category} className="rounded-2xl border border-white/10 bg-black/10 p-4">
                    <div className="mb-2 flex items-center justify-between text-sm">
                      <span className="text-stone-200">{CATEGORY_LABELS[category] ?? category}</span>
                      <span className="font-mono text-stone-400">{count}</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-stone-400">No category trends yet.</p>
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

function Pill({ label, value }: { label: string; value: string }) {
  return (
    <span className="rounded-full border border-white/10 bg-black/20 px-3 py-2 text-xs uppercase tracking-[0.18em]">
      {label}: {value}
    </span>
  )
}
