import Link from "next/link";
import { api } from "@/lib/api";
import { getRequestContextHeaders } from "@/lib/request-context";

export default async function WeeklyDigestsPage() {
  const requestHeaders = await getRequestContextHeaders()
  const digests = await api.getWeeklyDigests({ headers: requestHeaders });

  return (
    <main className="min-h-screen p-8 max-w-3xl mx-auto">
      <div className="flex items-center gap-4 mb-6">
        <Link href="/" className="text-sm text-gray-500 hover:underline">← ダッシュボード</Link>
        <h1 className="text-2xl font-bold">週報一覧</h1>
      </div>

      {!digests || digests.length === 0 ? (
        <p className="text-gray-500">週報がまだありません。</p>
      ) : (
        <div className="space-y-4">
          {digests.map((d) => (
            <Link key={d.id} href={`/weekly-digests/${d.id}`}>
              <div className="bg-white rounded-xl shadow p-5 hover:shadow-md transition-shadow">
                <div className="flex justify-between items-start mb-2">
                  <span className="font-semibold">{d.year}年 第{d.week}週</span>
                  <div className="flex gap-3 text-xs text-gray-500">
                    <span>PR {d.pr_count}件</span>
                    <span>学び {d.learning_count}件</span>
                  </div>
                </div>
                <p className="text-sm text-gray-600 line-clamp-2">{d.summary}</p>
              </div>
            </Link>
          ))}
        </div>
      )}
    </main>
  );
}
