import Link from "next/link"
import { notFound } from "next/navigation"
import { api } from "@/lib/api"
import {
  CATEGORY_LABELS,
  LEARNING_STATUS_COLORS,
  LEARNING_STATUS_LABELS,
} from "@/lib/learning-item-labels"
import type { RelatedLearningItem } from "@/lib/api"
import { getRequestContextHeaders } from "@/lib/request-context"

const MATCH_TYPE_LABELS: Record<RelatedLearningItem["match_types"][number], string> = {
  content_match: "Content match",
  review_match: "Review match",
  file_path_match: "File path match",
}

const MATCH_TYPE_COLORS: Record<RelatedLearningItem["match_types"][number], string> = {
  content_match: "border-sky-300/20 bg-sky-300/10 text-sky-100",
  review_match: "border-amber-300/20 bg-amber-300/10 text-amber-100",
  file_path_match: "border-fuchsia-300/20 bg-fuchsia-300/10 text-fuchsia-100",
}

export default async function PullRequestDetailPage({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = await params
  const requestHeaders = await getRequestContextHeaders()
  const pullRequest = await api.getPullRequest(Number(id), { headers: requestHeaders })

  if (!pullRequest) notFound()

  return (
    <main className="mx-auto min-h-screen max-w-6xl px-6 py-10">
      <div className="mb-6 flex flex-wrap items-center gap-4">
        <Link href="/learning-items" className="text-sm text-stone-400 hover:text-stone-200">
          Learning Items
        </Link>
        <h1 className="text-3xl font-semibold text-white">
          PR #{pullRequest.github_pr_number}
        </h1>
        <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-stone-300">
          {pullRequest.state}
        </span>
      </div>

      <section className="mb-6 rounded-[1.5rem] border border-white/10 bg-white/5 p-6 backdrop-blur">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-2xl font-semibold text-white">{pullRequest.title}</h2>
            <p className="mt-1 text-sm text-stone-400">Author: {pullRequest.author}</p>
          </div>
          <a
            href={pullRequest.github_url}
            target="_blank"
            rel="noreferrer"
            className="rounded-full bg-amber-300 px-4 py-2 text-sm font-medium text-stone-950"
          >
            Open on GitHub
          </a>
        </div>
      </section>

      <div className="grid gap-6 lg:grid-cols-[1.05fr_0.95fr]">
        <section className="rounded-[1.5rem] border border-white/10 bg-white/5 p-6 backdrop-blur">
          <h2 className="mb-4 text-xl font-semibold text-white">Extracted Learning Items</h2>
          {pullRequest.learning_items.length ? (
            <div className="space-y-4">
              {pullRequest.learning_items.map((item) => (
                <article key={item.id} className="rounded-2xl border border-white/10 bg-black/10 p-4">
                  <div className="mb-2 flex flex-wrap items-center gap-2">
                    <h3 className="font-medium text-white">{item.title}</h3>
                    <span className="rounded-full bg-white/10 px-2 py-0.5 text-xs text-stone-300">
                      {CATEGORY_LABELS[item.category] ?? item.category}
                    </span>
                    <span
                      className={`rounded-full border px-2 py-0.5 text-xs ${LEARNING_STATUS_COLORS[item.status]}`}
                    >
                      {LEARNING_STATUS_LABELS[item.status]}
                    </span>
                  </div>
                  <p className="mb-3 text-sm leading-6 text-stone-300">{item.detail}</p>
                  <div className="rounded-2xl border border-sky-300/15 bg-sky-300/10 p-3">
                    <p className="mb-1 text-[11px] uppercase tracking-[0.22em] text-sky-200/80">Next Action</p>
                    <p className="text-sm text-stone-100">{item.action_for_next_time}</p>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <p className="text-sm text-stone-400">No extracted learning items for this pull request yet.</p>
          )}
        </section>

        <section className="rounded-[1.5rem] border border-white/10 bg-white/5 p-6 backdrop-blur">
          <h2 className="mb-2 text-xl font-semibold text-white">Before You Repeat This</h2>
          <p className="mb-4 text-sm leading-6 text-stone-400">
            Similar learning items from earlier pull requests in the same workspace.
          </p>
          {pullRequest.related_learning_items.length ? (
            <div className="space-y-4">
              {pullRequest.related_learning_items.map((item) => (
                <article key={item.id} className="rounded-2xl border border-white/10 bg-black/10 p-4">
                  <div className="mb-2 flex flex-wrap items-center gap-2">
                    <h3 className="font-medium text-white">{item.title}</h3>
                    <span className="rounded-full bg-white/10 px-2 py-0.5 text-xs text-stone-300">
                      {CATEGORY_LABELS[item.category] ?? item.category}
                    </span>
                    <span
                      className={`rounded-full border px-2 py-0.5 text-xs ${LEARNING_STATUS_COLORS[item.status]}`}
                    >
                      {LEARNING_STATUS_LABELS[item.status]}
                    </span>
                    {item.same_repository ? (
                      <span className="rounded-full bg-amber-300/15 px-2 py-0.5 text-xs text-amber-100">
                        Same repository
                      </span>
                    ) : null}
                    <span className="rounded-full border border-emerald-300/20 bg-emerald-300/10 px-2 py-0.5 text-xs text-emerald-100">
                      Priority {item.relevance_score}
                    </span>
                  </div>
                  <p className="mb-2 text-xs uppercase tracking-[0.18em] text-stone-500">
                    {item.repository.full_name} / PR #{item.pull_request.github_pr_number}
                  </p>
                  <p className="mb-3 text-sm leading-6 text-stone-300">{item.detail}</p>
                  <div className="mb-3 flex flex-wrap gap-2">
                    {item.match_types.map((type) => (
                      <span
                        key={type}
                        className={`rounded-full border px-2 py-0.5 text-xs ${MATCH_TYPE_COLORS[type]}`}
                      >
                        {MATCH_TYPE_LABELS[type]}
                      </span>
                    ))}
                  </div>
                  <div className="mb-3 flex flex-wrap gap-2">
                    {item.recommendation_reasons.map((reason) => (
                      <span
                        key={reason}
                        className="rounded-full border border-emerald-300/20 bg-emerald-300/10 px-2 py-0.5 text-xs text-emerald-100"
                      >
                        {reason}
                      </span>
                    ))}
                  </div>
                  <div className="mb-3 flex flex-wrap gap-2">
                    {item.matched_terms.map((term) => (
                      <span key={term} className="rounded-full border border-sky-300/20 bg-sky-300/10 px-2 py-0.5 text-xs text-sky-100">
                        {term}
                      </span>
                    ))}
                  </div>
                  <div className="rounded-2xl border border-sky-300/15 bg-sky-300/10 p-3">
                    <p className="mb-1 text-[11px] uppercase tracking-[0.22em] text-sky-200/80">Carry Forward</p>
                    <p className="text-sm text-stone-100">{item.action_for_next_time}</p>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <p className="text-sm text-stone-400">No similar learning items were found yet.</p>
          )}
        </section>
      </div>
    </main>
  )
}
