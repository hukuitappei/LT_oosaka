import { cookies } from "next/headers"
import { SPACE_COOKIE, TOKEN_COOKIE, WORKSPACE_COOKIE } from "@/lib/auth"

export async function getRequestContextHeaders(extra?: HeadersInit): Promise<Headers> {
  const headers = new Headers(extra)
  const cookieStore = await cookies()

  const token = cookieStore.get(TOKEN_COOKIE)?.value
  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`)
  }

  const spaceId = cookieStore.get(SPACE_COOKIE)?.value ?? cookieStore.get(WORKSPACE_COOKIE)?.value
  if (spaceId && !headers.has("X-Space-Id")) {
    headers.set("X-Space-Id", spaceId)
  }
  if (spaceId && !headers.has("X-Workspace-Id")) {
    headers.set("X-Workspace-Id", spaceId)
  }

  return headers
}
