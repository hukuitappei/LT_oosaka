import Link from "next/link"
import { LearningItemsBoard } from "@/components/LearningItemsBoard"
import { api, type LearningItemStatus } from "@/lib/api"
import { CATEGORY_LABELS, LEARNING_STATUS_LABELS } from "@/lib/learning-item-labels"
import { getRequestContextHeaders } from "@/lib/request-context"

function readSearchParam(value: string | string[] | undefined): string {
  if (Array.isArray(value)) return value[0] ?? ""
  return value ?? ""
}

function toInt(value: string): number | undefined {
  if (!value) return undefined
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : undefined
}

function toStatus(value: string): LearningItemStatus | undefined {
  if (value === "new" || value === "in_progress" || value === "applied" || value === "ignored") {
    return value
  }
  return undefined
}

export default async function LearningItemsPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>
}) {
  const params = await searchParams
  const q = readSearchParam(params.q)
  const category = readSearchParam(params.category)
  const status = toStatus(readSearchParam(params.status))
  const repositoryId = toInt(readSearchParam(params.repository_id))

  const requestHeaders = await getRequestContextHeaders()
  const [items, summary, repositories] = await Promise.all([
    api.getLearningItems({
      headers: requestHeaders,
      query: {
        q: q || undefined,
        category: category || undefined,
        status: status || undefined,
        repository_id: repositoryId,
      },
    }),
    api.getLearningItemsSummary({ headers: requestHeaders }),
    api.getRepositories({ headers: requestHeaders }),
  ])

  const statusCounts = Object.fromEntries((summary?.status_counts ?? []).map((row) => [row.status, row.count]))

  return (
    <main className="mx-auto min-h-screen max-w-6xl px-6 py-10">
      <div className="mb-6 flex flex-wrap items-center gap-4">
        <Link href="/" className="text-sm text-stone-400 hover:text-stone-200">
          Dashboard
        </Link>
        <h1 className="text-3xl font-semibold text-white">Learning Items</h1>
        <span className="ml-auto text-sm text-stone-500">{items?.length ?? 0} shown</span>
      </div>

      <section className="mb-6 rounded-[1.5rem] border border-white/10 bg-white/5 p-6 backdrop-blur">
        <div className="mb-5 grid gap-4 md:grid-cols-4">
          <SummaryCard label="All Items" value={summary?.total_learning_items ?? 0} />
          <SummaryCard label="New" value={statusCounts.new ?? 0} />
          <SummaryCard label="In Progress" value={statusCounts.in_progress ?? 0} />
          <SummaryCard label="This Week" value={summary?.current_week_count ?? 0} />
        </div>

        <form className="grid gap-3 md:grid-cols-[2fr_1fr_1fr_1fr_auto]">
          <input
            type="search"
            name="q"
            defaultValue={q}
            placeholder="Search title, evidence, PR, repository"
            className="rounded-xl border border-white/10 bg-black/10 px-3 py-2 text-sm text-white placeholder:text-stone-500"
          />
          <select
            name="category"
            defaultValue={category}
            className="rounded-xl border border-white/10 bg-black/10 px-3 py-2 text-sm text-white"
          >
            <option value="">All categories</option>
            {Object.entries(CATEGORY_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
          <select
            name="status"
            defaultValue={status ?? ""}
            className="rounded-xl border border-white/10 bg-black/10 px-3 py-2 text-sm text-white"
          >
            <option value="">All statuses</option>
            {Object.entries(LEARNING_STATUS_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
          <select
            name="repository_id"
            defaultValue={repositoryId ? String(repositoryId) : ""}
            className="rounded-xl border border-white/10 bg-black/10 px-3 py-2 text-sm text-white"
          >
            <option value="">All repositories</option>
            {(repositories ?? []).map((repository) => (
              <option key={repository.id} value={repository.id}>
                {repository.full_name}
              </option>
            ))}
          </select>
          <div className="flex gap-2">
            <button
              type="submit"
              className="rounded-xl bg-amber-300 px-4 py-2 text-sm font-medium text-stone-950"
            >
              Filter
            </button>
            <Link
              href="/learning-items"
              className="rounded-xl border border-white/10 px-4 py-2 text-sm text-stone-200 hover:bg-white/10"
            >
              Reset
            </Link>
          </div>
        </form>
      </section>

      {!items || items.length === 0 ? (
        <p className="text-stone-400" data-testid="learning-items-empty-state">
          学びはまだありません。
        </p>
      ) : (
        <LearningItemsBoard initialItems={items} />
      )}
    </main>
  )
}

function SummaryCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-[1.25rem] border border-white/10 bg-black/10 p-4">
      <p className="mb-1 text-sm text-stone-400">{label}</p>
      <p className="text-2xl font-semibold text-white">{value}</p>
    </div>
  )
}
