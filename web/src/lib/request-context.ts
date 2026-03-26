import { cookies } from "next/headers"
import { TOKEN_COOKIE, WORKSPACE_COOKIE } from "@/lib/auth"

export async function getRequestContextHeaders(extra?: HeadersInit): Promise<Headers> {
  const headers = new Headers(extra)
  const cookieStore = await cookies()

  const token = cookieStore.get(TOKEN_COOKIE)?.value
  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`)
  }

  const workspaceId = cookieStore.get(WORKSPACE_COOKIE)?.value
  if (workspaceId && !headers.has("X-Workspace-Id")) {
    headers.set("X-Workspace-Id", workspaceId)
  }

  return headers
}
