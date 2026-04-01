"use client"

import { startTransition, useState } from "react"
import { useRouter } from "next/navigation"
import { api, type LearningItem, type LearningItemStatus } from "@/lib/api"
import {
  CATEGORY_COLORS,
  CATEGORY_LABELS,
  LEARNING_STATUS_COLORS,
  LEARNING_STATUS_LABELS,
} from "@/lib/learning-item-labels"

const STATUS_ORDER: LearningItemStatus[] = ["new", "in_progress", "applied", "ignored"]

export function LearningItemsBoard({
  initialItems,
}: {
  initialItems: LearningItem[]
}) {
  const router = useRouter()
  const [items, setItems] = useState(initialItems)
  const [pendingItemId, setPendingItemId] = useState<number | null>(null)
  const [error, setError] = useState("")

  async function updateStatus(itemId: number, nextStatus: LearningItemStatus) {
    const previousItems = items
    setError("")
    setPendingItemId(itemId)
    setItems((current) =>
      current.map((item) => (item.id === itemId ? { ...item, status: nextStatus } : item)),
    )

    const updated = await api.updateLearningItem(itemId, { status: nextStatus })
    if (!updated) {
      setItems(previousItems)
      setError("Failed to update the learning item status.")
      setPendingItemId(null)
      return
    }

    setItems((current) => current.map((item) => (item.id === itemId ? updated : item)))
    setPendingItemId(null)
    startTransition(() => {
      router.refresh()
    })
  }

  if (!items.length) {
    return <p className="text-sm text-stone-400">No learning items matched the current filters.</p>
  }

  return (
    <div className="space-y-4">
      {error ? <p className="text-sm text-red-400">{error}</p> : null}
      {items.map((item) => (
        <article key={item.id} className="rounded-[1.5rem] border border-white/10 bg-white/5 p-5 backdrop-blur">
          <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
            <div>
              <div className="mb-2 flex flex-wrap items-center gap-2">
                <h3 className="text-lg font-semibold text-white">{item.title}</h3>
                <span
                  className={`rounded-full px-2 py-0.5 text-xs ${CATEGORY_COLORS[item.category] ?? CATEGORY_COLORS.other}`}
                >
                  {CATEGORY_LABELS[item.category] ?? item.category}
                </span>
                <span
                  className={`rounded-full border px-2 py-0.5 text-xs ${LEARNING_STATUS_COLORS[item.status]}`}
                >
                  {LEARNING_STATUS_LABELS[item.status]}
                </span>
              </div>
              <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-stone-400">
                <span>{item.repository.full_name}</span>
                <span>PR #{item.pull_request.github_pr_number}</span>
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
            <div className="flex flex-wrap gap-2">
              {STATUS_ORDER.map((status) => (
                <button
                  key={status}
                  type="button"
                  disabled={pendingItemId === item.id || item.status === status}
                  onClick={() => updateStatus(item.id, status)}
                  className={`rounded-full border px-3 py-1 text-xs transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${
                    item.status === status
                      ? "border-white/30 bg-white/15 text-white"
                      : "border-white/10 bg-black/10 text-stone-300 hover:bg-white/10"
                  }`}
                >
                  {LEARNING_STATUS_LABELS[status]}
                </button>
              ))}
            </div>
          </div>

          <p className="mb-3 text-sm leading-6 text-stone-300">{item.detail}</p>

          <div className="mb-3 rounded-2xl border border-amber-300/15 bg-amber-300/10 p-3">
            <p className="mb-1 text-[11px] uppercase tracking-[0.22em] text-amber-200/80">Evidence</p>
            <p className="text-sm text-stone-200">{item.evidence}</p>
          </div>

          <div className="rounded-2xl border border-sky-300/15 bg-sky-300/10 p-3">
            <p className="mb-1 text-[11px] uppercase tracking-[0.22em] text-sky-200/80">Next Action</p>
            <p className="text-sm text-stone-100">{item.action_for_next_time}</p>
          </div>
        </article>
      ))}
    </div>
  )
}
