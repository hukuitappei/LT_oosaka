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
        : "Failed to load GitHub connections. Check the authentication state and API connectivity."
  }

  return (
    <main className="mx-auto min-h-screen max-w-6xl px-6 py-10">
      <div className="mb-8">
        <Link href="/" className="text-sm text-stone-400 hover:text-stone-200">
          Home
        </Link>
        <h1 className="mt-3 text-3xl font-semibold text-white" data-testid="github-connections-title">
          GitHub connections
        </h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-stone-300">
          Manage the personal tokens and GitHub App installations used by the current workspace.
        </p>
      </div>

      <GitHubConnectionsManager initialConnections={connections} initialError={initialError} />
    </main>
  )
}
