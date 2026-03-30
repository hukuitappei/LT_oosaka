import Link from "next/link"
import GitHubConnectionsManager from "@/components/GitHubConnectionsManager"
import { api } from "@/lib/api"
import { getRequestContextHeaders } from "@/lib/request-context"

export default async function GitHubConnectionsPage() {
  const requestHeaders = await getRequestContextHeaders()
  const connections = (await api.getGitHubConnections({ headers: requestHeaders })) ?? []

  return (
    <main className="mx-auto min-h-screen max-w-6xl px-6 py-10">
      <div className="mb-8">
        <Link href="/" className="text-sm text-stone-400 hover:text-stone-200">
          ホーム
        </Link>
        <h1 className="mt-3 text-3xl font-semibold text-white">GitHub 接続</h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-stone-300">
          token 接続と app 連携をこの画面でまとめて管理します。現在の workspace に表示される接続だけが対象です。
        </p>
      </div>

      <GitHubConnectionsManager initialConnections={connections} />
    </main>
  )
}
