const API_URL = process.env.API_URL || "http://localhost:8000"

export interface LearningItem {
  id: number
  pull_request_id: number
  title: string
  detail: string
  category: string
  confidence: number
  action_for_next_time: string
  evidence: string
  created_at: string
}

export interface WeeklyDigest {
  id: number
  year: number
  week: number
  summary: string
  repeated_issues: string[]
  next_time_notes: string[]
  pr_count: number
  learning_count: number
  created_at: string
}

export interface Repository {
  id: number
  github_id: number
  full_name: string
  name: string
  created_at: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
}

// クッキーからトークンを取得（Server Component 向け）
function getTokenFromCookie(): string | null {
  if (typeof document === "undefined") return null
  const match = document.cookie.match(/(?:^|;\s*)token=([^;]*)/)
  return match ? match[1] : null
}

async function apiFetch<T>(path: string, token?: string): Promise<T | null> {
  const headers: Record<string, string> = {}
  const t = token ?? getTokenFromCookie()
  if (t) headers["Authorization"] = `Bearer ${t}`

  try {
    const res = await fetch(`${API_URL}${path}`, {
      cache: "no-store",
      headers,
    })
    if (!res.ok) return null
    return res.json()
  } catch {
    return null
  }
}

export async function login(email: string, password: string): Promise<TokenResponse> {
  const form = new URLSearchParams({ username: email, password })
  const res = await fetch(`${API_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: form.toString(),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail ?? "Login failed")
  }
  return res.json()
}

export async function register(email: string, password: string): Promise<TokenResponse> {
  const res = await fetch(`${API_URL}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail ?? "Registration failed")
  }
  return res.json()
}

export const api = {
  getLearningItems: (token?: string) => apiFetch<LearningItem[]>("/learning-items/", token),
  getWeeklyDigests: (token?: string) => apiFetch<WeeklyDigest[]>("/weekly-digests/", token),
  getWeeklyDigest: (id: number, token?: string) =>
    apiFetch<WeeklyDigest>(`/weekly-digests/${id}`, token),
  getRepositories: (token?: string) => apiFetch<Repository[]>("/repositories/", token),
}
