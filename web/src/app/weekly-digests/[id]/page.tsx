import Link from "next/link";
import { api } from "@/lib/api";
import { notFound } from "next/navigation";

export default async function WeeklyDigestDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const digest = await api.getWeeklyDigest(Number(id));
  if (!digest) notFound();

  return (
    <main className="min-h-screen p-8 max-w-3xl mx-auto">
      <div className="flex items-center gap-4 mb-6">
        <Link href="/weekly-digests" className="text-sm text-gray-500 hover:underline">← 週報一覧</Link>
        <h1 className="text-2xl font-bold">{digest.year}年 第{digest.week}週の週報</h1>
      </div>

      <div className="flex gap-4 text-sm text-gray-500 mb-6">
        <span>PR {digest.pr_count}件</span>
        <span>学び {digest.learning_count}件</span>
      </div>

      <section className="bg-white rounded-xl shadow p-6 mb-5">
        <h2 className="font-semibold mb-3">今週のまとめ</h2>
        <p className="text-gray-700 leading-relaxed">{digest.summary}</p>
      </section>

      {digest.repeated_issues.length > 0 && (
        <section className="bg-white rounded-xl shadow p-6 mb-5">
          <h2 className="font-semibold mb-3">繰り返し出てきた詰まり</h2>
          <ul className="space-y-1">
            {digest.repeated_issues.map((issue, i) => (
              <li key={i} className="flex gap-2 text-sm text-gray-700">
                <span className="text-orange-500 mt-0.5">▲</span>
                {issue}
              </li>
            ))}
          </ul>
        </section>
      )}

      {digest.next_time_notes.length > 0 && (
        <section className="bg-white rounded-xl shadow p-6">
          <h2 className="font-semibold mb-3">次週の自分へ</h2>
          <ul className="space-y-1">
            {digest.next_time_notes.map((note, i) => (
              <li key={i} className="flex gap-2 text-sm text-gray-700">
                <span className="text-blue-500 mt-0.5">→</span>
                {note}
              </li>
            ))}
          </ul>
        </section>
      )}
    </main>
  );
}
