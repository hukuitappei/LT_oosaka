async function getHealth() {
  try {
    const apiUrl = process.env.API_URL || "http://localhost:8000";
    const res = await fetch(`${apiUrl}/health`, { cache: "no-store" });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

function StatusBadge({ status }: { status: string }) {
  const ok = status === "ok";
  return (
    <span
      className={`inline-block px-2 py-0.5 rounded text-sm font-mono ${
        ok ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800"
      }`}
    >
      {status}
    </span>
  );
}

export default async function Home() {
  const health = await getHealth();

  return (
    <main className="min-h-screen flex flex-col items-center justify-center p-8">
      <h1 className="text-3xl font-bold mb-2">週報AI</h1>
      <p className="text-gray-500 mb-8">試行錯誤を知識に変えるシステム</p>

      <div className="bg-white rounded-xl shadow p-6 w-full max-w-md">
        <h2 className="font-semibold mb-4">システム状態</h2>
        {health ? (
          <table className="w-full text-sm">
            <tbody>
              {Object.entries(health).map(([key, val]) => (
                <tr key={key} className="border-b last:border-0">
                  <td className="py-2 font-medium text-gray-600 capitalize">{key}</td>
                  <td className="py-2 text-right">
                    <StatusBadge status={String(val)} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="text-red-500 text-sm">APIに接続できません</p>
        )}
      </div>
    </main>
  );
}
