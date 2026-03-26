const TOKEN_KEY = "auth_token"

export function getToken(): string | null {
  if (typeof window === "undefined") return null
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
  // middleware でリダイレクト判定に使用するクッキーをセット (7日間)
  document.cookie = `token=${token}; path=/; max-age=${60 * 60 * 24 * 7}; SameSite=Lax`
}

export function removeToken(): void {
  localStorage.removeItem(TOKEN_KEY)
  document.cookie = "token=; path=/; max-age=0"
}

export function isAuthenticated(): boolean {
  return !!getToken()
}
