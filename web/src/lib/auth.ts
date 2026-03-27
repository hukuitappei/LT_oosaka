export const TOKEN_KEY = "auth_token"
export const WORKSPACE_KEY = "workspace_id"
export const TOKEN_COOKIE = "token"
export const WORKSPACE_COOKIE = "workspace_id"
export const EMAIL_KEY = "auth_email"

const COOKIE_MAX_AGE = 60 * 60 * 24 * 7

function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null
  const match = document.cookie.match(new RegExp(`(?:^|;\\s*)${name}=([^;]*)`))
  return match ? decodeURIComponent(match[1]) : null
}

function writeCookie(name: string, value: string): void {
  if (typeof document === "undefined") return
  document.cookie = `${name}=${encodeURIComponent(value)}; path=/; max-age=${COOKIE_MAX_AGE}; SameSite=Lax`
}

function clearCookie(name: string): void {
  if (typeof document === "undefined") return
  document.cookie = `${name}=; path=/; max-age=0; SameSite=Lax`
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null
  return readCookie(TOKEN_COOKIE) ?? localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string): void {
  if (typeof window === "undefined") return
  localStorage.setItem(TOKEN_KEY, token)
  writeCookie(TOKEN_COOKIE, token)
}

export function getUserEmail(): string | null {
  if (typeof window === "undefined") return null
  return localStorage.getItem(EMAIL_KEY)
}

export function setUserEmail(email: string): void {
  if (typeof window === "undefined") return
  localStorage.setItem(EMAIL_KEY, email)
}

export function removeToken(): void {
  if (typeof window === "undefined") return
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(EMAIL_KEY)
  clearCookie(TOKEN_COOKIE)
}

export function getWorkspaceId(): string | null {
  if (typeof window === "undefined") return null
  return readCookie(WORKSPACE_COOKIE) ?? localStorage.getItem(WORKSPACE_KEY)
}

export function setWorkspaceId(workspaceId: string): void {
  if (typeof window === "undefined") return
  localStorage.setItem(WORKSPACE_KEY, workspaceId)
  writeCookie(WORKSPACE_COOKIE, workspaceId)
}

export function removeWorkspaceId(): void {
  if (typeof window === "undefined") return
  localStorage.removeItem(WORKSPACE_KEY)
  clearCookie(WORKSPACE_COOKIE)
}

export function isAuthenticated(): boolean {
  return !!getToken()
}

export function getClientRequestHeaders(): Record<string, string> {
  const headers: Record<string, string> = {}
  const token = readCookie(TOKEN_COOKIE) ?? getToken()
  const workspaceId = readCookie(WORKSPACE_COOKIE) ?? getWorkspaceId()

  if (token) headers.Authorization = `Bearer ${token}`
  if (workspaceId) headers["X-Workspace-Id"] = workspaceId

  return headers
}
