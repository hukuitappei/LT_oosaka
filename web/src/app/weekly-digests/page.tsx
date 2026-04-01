import Link from "next/link"
import { api } from "@/lib/api"
import { getRequestContextHeaders } from "@/lib/request-context"

export default async function WeeklyDigestsPage() {
  const requestHeaders = await getRequestContextHeaders()
  const digests = await api.getWeeklyDigests({ headers: requestHeaders })

  return (
    <main className="mx-auto min-h-screen max-w-4xl px-6 py-10">
      <div className="mb-6 flex items-center gap-4">
        <Link href="/" className="text-sm text-stone-400 hover:text-stone-200">
          Dashboard
        </Link>
        <h1 className="text-2xl font-semibold text-white">Weekly Digests</h1>
      </div>

      {!digests || digests.length === 0 ? (
        <p className="text-stone-400">No weekly digests yet.</p>
      ) : (
        <div className="space-y-4">
          {digests.map((digest) => (
            <Link key={digest.id} href={`/weekly-digests/${digest.id}`}>
              <div className="rounded-[1.5rem] border border-white/10 bg-white/5 p-5 transition-colors hover:bg-white/10">
                <div className="mb-2 flex items-start justify-between gap-4">
                  <span className="font-semibold text-white">
                    {digest.year} Week {digest.week}
                  </span>
                  <div className="flex gap-3 text-xs text-stone-400">
                    <span>PRs {digest.pr_count}</span>
                    <span>Items {digest.learning_count}</span>
                  </div>
                </div>
                <p className="line-clamp-2 text-sm leading-6 text-stone-300">{digest.summary}</p>
              </div>
            </Link>
          ))}
        </div>
      )}
    </main>
  )
}
