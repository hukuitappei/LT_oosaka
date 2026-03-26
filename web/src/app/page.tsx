import Link from "next/link";
import { api } from "@/lib/api";

const CATEGORY_LABELS: Record<string, string> = {
  security: "セキュリティ",
  performance: "パフォーマンス",
  design: "設計",
  testing: "テスト",
  code_quality: "コード品質",
  other: "その他",
};

export default async function Home() {
  const [items, digests] = await Promise.all([
    api.getLearningItems(),
    api.getWeeklyDigests(),
  ]);

  const latestDigest = digests?.[0] ?? null;

  // カテゴリ別集計
  const categoryCounts: Record<string, number> = {};
  for (const item of items ?? []) {
    categoryCounts[item.category] = (categoryCounts[item.category] ?? 0) + 1;
  }
  const topCategories = Object.entries(categoryCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3);

  return (
    <main className="min-h-screen p-8 max-w-4xl mx-auto">
      <h1 className="text-3xl font-bold mb-1">週報AI</h1>
      <p className="text-gray-500 mb-8">試行錯誤を知識に変えるシステム</p>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <StatCard label="総学び件数" value={items?.length ?? 0} />
        <StatCard label="週報件数" value={digests?.length ?? 0} />
        <StatCard label="今週の学び" value={latestDigest?.learning_count ?? 0} />
      </div>

      {topCategories.length > 0 && (
        <section className="bg-white rounded-xl shadow p-6 mb-6">
          <h2 className="font-semibold mb-3">よく出るカテゴリ</h2>
          <div className="space-y-2">
            {topCategories.map(([cat, count]) => (
              <div key={cat} className="flex items-center gap-3">
                <span className="text-sm text-gray-600 w-32">
                  {CATEGORY_LABELS[cat] ?? cat}
                </span>
                <div className="flex-1 bg-gray-100 rounded-full h-2">
                  <div
                    className="bg-blue-500 h-2 rounded-full"
                    style={{ width: `${Math.min(100, (count / (items?.length ?? 1)) * 100)}%` }}
                  />
                </div>
                <span className="text-sm font-mono text-gray-700">{count}</span>
              </div>
            ))}
          </div>
        </section>
      )}

      {latestDigest && (
        <section className="bg-white rounded-xl shadow p-6 mb-6">
          <div className="flex justify-between items-start mb-2">
            <h2 className="font-semibold">最新週報</h2>
            <span className="text-xs text-gray-400">
              {latestDigest.year}年 第{latestDigest.week}週
            </span>
          </div>
          <p className="text-sm text-gray-700 mb-3 line-clamp-3">{latestDigest.summary}</p>
          <Link
            href={`/weekly-digests/${latestDigest.id}`}
            className="text-sm text-blue-600 hover:underline"
          >
            詳細を見る →
          </Link>
        </section>
      )}

      <nav className="flex gap-4">
        <Link href="/weekly-digests" className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700">
          週報一覧
        </Link>
        <Link href="/learning-items" className="px-4 py-2 bg-white border rounded-lg text-sm hover:bg-gray-50">
          学び一覧
        </Link>
      </nav>
    </main>
  );
}

function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="bg-white rounded-xl shadow p-5">
      <p className="text-sm text-gray-500 mb-1">{label}</p>
      <p className="text-3xl font-bold">{value}</p>
    </div>
  );
}
