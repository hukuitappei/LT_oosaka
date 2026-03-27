import Link from "next/link"
import { notFound } from "next/navigation"
import { api } from "@/lib/api"
import { getRequestContextHeaders } from "@/lib/request-context"

export default async function WeeklyDigestDetailPage({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = await params
  const requestHeaders = await getRequestContextHeaders()
  const digest = await api.getWeeklyDigest(Number(id), {
    headers: requestHeaders,
  })

  if (!digest) notFound()

  return (
    <main className="mx-auto min-h-screen max-w-4xl px-6 py-10">
      <div className="mb-6 flex items-center gap-4">
        <Link href="/weekly-digests" className="text-sm text-stone-400 hover:text-stone-200">
          ← Weekly Digests
        </Link>
        <h1 className="text-2xl font-semibold text-white">
          {digest.year}年 第{digest.week}週の Digest
        </h1>
      </div>

      <div className="mb-6 flex gap-4 text-sm text-stone-400">
        <span>PR {digest.pr_count}件</span>
        <span>Items {digest.learning_count}件</span>
      </div>

      <section className="mb-5 rounded-[1.5rem] border border-white/10 bg-white/5 p-6 backdrop-blur">
        <h2 className="mb-3 font-semibold text-white">今週の要約</h2>
        <p className="leading-7 text-stone-300">{digest.summary}</p>
      </section>

      {digest.repeated_issues.length > 0 && (
        <section className="mb-5 rounded-[1.5rem] border border-white/10 bg-white/5 p-6 backdrop-blur">
          <h2 className="mb-3 font-semibold text-white">繰り返し出ている課題</h2>
          <ul className="space-y-1">
            {digest.repeated_issues.map((issue, index) => (
              <li key={index} className="flex gap-2 text-sm text-stone-300">
                <span className="mt-0.5 text-amber-300">•</span>
                {issue}
              </li>
            ))}
          </ul>
        </section>
      )}

      {digest.next_time_notes.length > 0 && (
        <section className="rounded-[1.5rem] border border-white/10 bg-white/5 p-6 backdrop-blur">
          <h2 className="mb-3 font-semibold text-white">次回に向けたメモ</h2>
          <ul className="space-y-1">
            {digest.next_time_notes.map((note, index) => (
              <li key={index} className="flex gap-2 text-sm text-stone-300">
                <span className="mt-0.5 text-sky-300">•</span>
                {note}
              </li>
            ))}
          </ul>
        </section>
      )}
    </main>
  )
}
