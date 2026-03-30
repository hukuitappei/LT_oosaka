import Link from "next/link"
import GitHubConnectionsManager from "@/components/GitHubConnectionsManager"
import { ApiRequestError, api, type GitHubConnection } from "@/lib/api"
import { getRequestContextHeaders } from "@/lib/request-context"

export const dynamic = "force-dynamic"

export default async function GitHubConnectionsPage() {
  const requestHeaders = await getRequestContextHeaders()
  let connections: GitHubConnection[] = []
  let initialError = ""

  try {
    connections =
      (await api.getGitHubConnections({
        headers: requestHeaders,
        throwOnError: true,
      })) ?? []
  } catch (error) {
    initialError =
      error instanceof ApiRequestError
        ? error.message
        : "GitHub 接続の取得に失敗しました。認証情報と API 接続を確認してください。"
  }

  return (
    <main className="mx-auto min-h-screen max-w-6xl px-6 py-10">
      <div className="mb-8">
        <Link href="/" className="text-sm text-stone-400 hover:text-stone-200">
          ホーム
        </Link>
        <h1 className="mt-3 text-3xl font-semibold text-white" data-testid="github-connections-title">
          GitHub 接続
        </h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-stone-300">
          現在の workspace で利用する personal token と GitHub App installation を管理します。
        </p>
      </div>

      <GitHubConnectionsManager initialConnections={connections} initialError={initialError} />
    </main>
  )
}
