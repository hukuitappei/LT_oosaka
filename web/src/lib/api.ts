import { getClientRequestHeaders, getToken } from "@/lib/auth"

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
  visibility: string
  created_at: string
  repository: {
    id: number
    full_name: string
    name: string
  }
  pull_request: {
    id: number
    github_pr_number: number
    title: string
    github_url: string
  }
}

export interface WeeklyDigest {
  id: number
  workspace_id: number
  year: number
  week: number
  summary: string
  repeated_issues: string[]
  next_time_notes: string[]
  pr_count: number
  learning_count: number
  visibility: string
  created_at: string
}

export interface LearningItemsSummary {
  total_learning_items: number
  current_week_count: number
  weekly_points: Array<{
    year: number
    week: number
    label: string
    learning_count: number
  }>
  top_categories: Array<{
    category: string
    count: number
  }>
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
  default_workspace_id: number
}

export interface ApiFetchOptions {
  token?: string
  headers?: HeadersInit
}

function toHeaders(input?: HeadersInit): Headers {
  const headers = new Headers()

  if (!input) return headers

  if (input instanceof Headers) {
    input.forEach((value, key) => {
      headers.set(key, value)
    })
    return headers
  }

  if (Array.isArray(input)) {
    for (const [key, value] of input) {
      headers.set(key, value)
    }
    return headers
  }

  for (const [key, value] of Object.entries(input)) {
    if (typeof value === "string") {
      headers.set(key, value)
    }
  }

  return headers
}

async function apiFetch<T>(path: string, options: ApiFetchOptions = {}): Promise<T | null> {
  const headers = toHeaders(options.headers)
  const token = options.token ?? getToken()
  const clientHeaders = getClientRequestHeaders()

  if (token) {
    headers.set("Authorization", `Bearer ${token}`)
  } else if (clientHeaders.Authorization) {
    headers.set("Authorization", clientHeaders.Authorization)
  }

  if (!headers.has("X-Workspace-Id") && clientHeaders["X-Workspace-Id"]) {
    headers.set("X-Workspace-Id", clientHeaders["X-Workspace-Id"])
  }

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
  getLearningItems: (options?: ApiFetchOptions) =>
    apiFetch<LearningItem[]>("/learning-items/", options),
  getLearningItemsSummary: (options?: ApiFetchOptions) =>
    apiFetch<LearningItemsSummary>("/learning-items/summary", options),
  getWeeklyDigests: (options?: ApiFetchOptions) =>
    apiFetch<WeeklyDigest[]>("/weekly-digests/", options),
  getWeeklyDigest: (id: number, options?: ApiFetchOptions) =>
    apiFetch<WeeklyDigest>(`/weekly-digests/${id}`, options),
  getRepositories: (options?: ApiFetchOptions) =>
    apiFetch<Repository[]>("/repositories/", options),
}
