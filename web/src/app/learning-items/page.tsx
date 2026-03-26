import Link from "next/link";
import { api } from "@/lib/api";

const CATEGORY_COLORS: Record<string, string> = {
  security: "bg-red-100 text-red-800",
  performance: "bg-yellow-100 text-yellow-800",
  design: "bg-purple-100 text-purple-800",
  testing: "bg-green-100 text-green-800",
  code_quality: "bg-blue-100 text-blue-800",
  other: "bg-gray-100 text-gray-800",
};

const CATEGORY_LABELS: Record<string, string> = {
  security: "セキュリティ",
  performance: "パフォーマンス",
  design: "設計",
  testing: "テスト",
  code_quality: "コード品質",
  other: "その他",
};

export default async function LearningItemsPage() {
  const items = await api.getLearningItems();

  return (
    <main className="min-h-screen p-8 max-w-3xl mx-auto">
      <div className="flex items-center gap-4 mb-6">
        <Link href="/" className="text-sm text-gray-500 hover:underline">← ダッシュボード</Link>
        <h1 className="text-2xl font-bold">学び一覧</h1>
        <span className="text-sm text-gray-400 ml-auto">{items?.length ?? 0}件</span>
      </div>

      {!items || items.length === 0 ? (
        <p className="text-gray-500">学びがまだありません。</p>
      ) : (
        <div className="space-y-4">
          {items.map((item) => (
            <div key={item.id} className="bg-white rounded-xl shadow p-5">
              <div className="flex items-start justify-between gap-2 mb-2">
                <h3 className="font-semibold text-gray-900">{item.title}</h3>
                <span className={`text-xs px-2 py-0.5 rounded-full shrink-0 ${CATEGORY_COLORS[item.category] ?? CATEGORY_COLORS.other}`}>
                  {CATEGORY_LABELS[item.category] ?? item.category}
                </span>
              </div>
              <p className="text-sm text-gray-600 mb-3">{item.detail}</p>
              <div className="bg-gray-50 rounded p-3 text-xs text-gray-500 mb-3 italic">
                &ldquo;{item.evidence}&rdquo;
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-gray-400">次回アクション:</span>
                <span className="text-xs text-gray-700">{item.action_for_next_time}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </main>
  );
}
