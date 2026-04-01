import { getClientRequestHeaders, getToken } from "@/lib/auth"

const API_URL = process.env.API_URL || "http://localhost:8000"

export type LearningItemStatus = "new" | "in_progress" | "applied" | "ignored"

export interface LearningItem {
  id: number
  pull_request_id: number
  title: string
  detail: string
  category: string
  confidence: number
  action_for_next_time: string
  evidence: string
  status: LearningItemStatus
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
  status_counts: Array<{
    status: LearningItemStatus
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

export interface PullRequestDetailLearningItem {
  id: number
  title: string
  detail: string
  category: string
  confidence: number
  action_for_next_time: string
  evidence: string
  status: LearningItemStatus
  visibility: string
  created_at: string
}

export interface RelatedLearningItem extends LearningItem {
  repository: LearningItem["repository"]
  pull_request: LearningItem["pull_request"]
  matched_terms: string[]
  same_repository: boolean
}

export interface PullRequestDetail {
  id: number
  github_pr_number: number
  title: string
  state: string
  author: string
  github_url: string
  processed: boolean
  created_at: string
  learning_items: PullRequestDetailLearningItem[]
  related_learning_items: RelatedLearningItem[]
}

export interface TokenResponse {
  access_token: string
  token_type: string
  default_workspace_id: number
}

type QueryValue = string | number | boolean | null | undefined

export interface ApiRequestOptions {
  token?: string
  headers?: HeadersInit
  query?: Record<string, QueryValue>
  method?: string
  body?: BodyInit | null
}

export interface UpdateLearningItemInput {
  status?: LearningItemStatus
  visibility?: string
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

function buildUrl(path: string, query?: Record<string, QueryValue>): string {
  const url = new URL(path, API_URL)
  if (!query) return url.toString()

  for (const [key, value] of Object.entries(query)) {
    if (value === undefined || value === null || value === "") continue
    url.searchParams.set(key, String(value))
  }

  return url.toString()
}

async function apiRequest<T>(path: string, options: ApiRequestOptions = {}): Promise<T | null> {
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
    const res = await fetch(buildUrl(path, options.query), {
      method: options.method ?? "GET",
      cache: "no-store",
      headers,
      body: options.body ?? null,
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
  getLearningItems: (
    options?: ApiRequestOptions & {
      query?: {
        q?: string
        repository_id?: number
        pr_id?: number
        category?: string
        status?: LearningItemStatus
        visibility?: string
        limit?: number
        offset?: number
      }
    },
  ) => apiRequest<LearningItem[]>("/learning-items/", options),
  getLearningItemsSummary: (options?: ApiRequestOptions & { query?: { weeks?: number } }) =>
    apiRequest<LearningItemsSummary>("/learning-items/summary", options),
  updateLearningItem: (id: number, input: UpdateLearningItemInput, options?: ApiRequestOptions) =>
    apiRequest<LearningItem>(`/learning-items/${id}`, {
      ...options,
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        ...(options?.headers ?? {}),
      },
      body: JSON.stringify(input),
    }),
  getWeeklyDigests: (options?: ApiRequestOptions) =>
    apiRequest<WeeklyDigest[]>("/weekly-digests/", options),
  getWeeklyDigest: (id: number, options?: ApiRequestOptions) =>
    apiRequest<WeeklyDigest>(`/weekly-digests/${id}`, options),
  getPullRequest: (id: number, options?: ApiRequestOptions) =>
    apiRequest<PullRequestDetail>(`/pull-requests/${id}`, options),
  getRepositories: (options?: ApiRequestOptions) =>
    apiRequest<Repository[]>("/repositories/", options),
}
