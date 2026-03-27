import Link from "next/link"
import { api } from "@/lib/api"
import { getRequestContextHeaders } from "@/lib/request-context"

const CATEGORY_COLORS: Record<string, string> = {
  security: "bg-red-100 text-red-800",
  performance: "bg-yellow-100 text-yellow-800",
  design: "bg-purple-100 text-purple-800",
  testing: "bg-green-100 text-green-800",
  code_quality: "bg-blue-100 text-blue-800",
  other: "bg-gray-100 text-gray-800",
}

const CATEGORY_LABELS: Record<string, string> = {
  security: "セキュリティ",
  performance: "パフォーマンス",
  design: "設計",
  testing: "テスト",
  code_quality: "コード品質",
  other: "その他",
}

export default async function LearningItemsPage() {
  const requestHeaders = await getRequestContextHeaders()
  const items = await api.getLearningItems({ headers: requestHeaders })

  return (
    <main className="mx-auto min-h-screen max-w-4xl px-6 py-10">
      <div className="mb-6 flex items-center gap-4">
        <Link href="/" className="text-sm text-stone-400 hover:text-stone-200">
          ← Dashboard
        </Link>
        <h1 className="text-2xl font-semibold text-white">Learning Items</h1>
        <span className="ml-auto text-sm text-stone-500">{items?.length ?? 0}件</span>
      </div>

      {!items || items.length === 0 ? (
        <p className="text-stone-400">学びがまだありません。</p>
      ) : (
        <div className="space-y-4">
          {items.map((item) => (
            <div key={item.id} className="rounded-[1.5rem] border border-white/10 bg-white/5 p-5 backdrop-blur">
              <div className="mb-2 flex items-start justify-between gap-2">
                <h3 className="font-semibold text-white">{item.title}</h3>
                <span
                  className={`shrink-0 rounded-full px-2 py-0.5 text-xs ${CATEGORY_COLORS[item.category] ?? CATEGORY_COLORS.other}`}
                >
                  {CATEGORY_LABELS[item.category] ?? item.category}
                </span>
              </div>
              <div className="mb-3 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-stone-500">
                <span>{item.repository.full_name}</span>
                <span>PR #{item.pull_request.github_pr_number}</span>
                <a
                  href={item.pull_request.github_url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-sky-300 hover:text-sky-200"
                >
                  GitHub
                </a>
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
            </div>
          ))}
        </div>
      )}
    </main>
  )
}
