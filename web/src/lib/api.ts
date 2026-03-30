import { getClientRequestHeaders, getToken } from "@/lib/auth"

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

export interface GitHubConnection {
  id: number
  provider_type: string
  workspace_id: number | null
  user_id: number | null
  installation_id: number | null
  github_account_login: string | null
  label: string | null
  is_active: boolean
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
  throwOnError?: boolean
}

export interface ApiRequestOptions extends ApiFetchOptions {
  method?: string
  body?: unknown
}

export class ApiRequestError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = "ApiRequestError"
    this.status = status
  }
}

function getApiBaseUrl(): string {
  if (typeof window !== "undefined") {
    return "/api/backend"
  }
  return process.env.API_URL || "http://localhost:8000"
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
    const hasBody = options.body !== undefined
    if (hasBody && !headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json")
    }

    const res = await fetch(`${getApiBaseUrl()}${path}`, {
      method: options.method ?? "GET",
      cache: "no-store",
      headers,
      body: hasBody
        ? typeof options.body === "string" || options.body instanceof FormData
          ? options.body
          : JSON.stringify(options.body)
        : undefined,
    })
    if (!res.ok) {
      if (!options.throwOnError) return null
      const error = await res.json().catch(() => null)
      throw new ApiRequestError(error?.detail ?? `Request failed with status ${res.status}`, res.status)
    }
    if (res.status === 204) return null
    return res.json()
  } catch (error) {
    if (options.throwOnError) {
      if (error instanceof Error) {
        throw error
      }
      throw new ApiRequestError("Network request failed", 0)
    }
    return null
  }
}

async function apiFetch<T>(path: string, options: ApiFetchOptions = {}): Promise<T | null> {
  return apiRequest<T>(path, options)
}

export async function login(email: string, password: string): Promise<TokenResponse> {
  const form = new URLSearchParams({ username: email, password })
  const res = await fetch(`${getApiBaseUrl()}/auth/login`, {
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
  const res = await fetch(`${getApiBaseUrl()}/auth/register`, {
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
  getGitHubConnections: (options?: ApiFetchOptions) =>
    apiFetch<GitHubConnection[]>("/github-connections/", options),
  createTokenGitHubConnection: (
    payload: {
      access_token: string
      github_account_login?: string | null
      label?: string | null
      workspace_id?: number | null
    },
    options?: ApiFetchOptions,
  ) =>
    apiRequest<GitHubConnection>("/github-connections/token", {
      ...options,
      throwOnError: options?.throwOnError ?? true,
      method: "POST",
      body: payload,
    }),
  linkAppGitHubConnection: (
    payload: {
      installation_id: number
      github_account_login?: string | null
      label?: string | null
      workspace_id?: number | null
    },
    options?: ApiFetchOptions,
  ) =>
    apiRequest<GitHubConnection>("/github-connections/app/link", {
      ...options,
      throwOnError: options?.throwOnError ?? true,
      method: "POST",
      body: payload,
    }),
  deleteGitHubConnection: (connectionId: number, options?: ApiFetchOptions) =>
    apiRequest<{ status: string }>(`/github-connections/${connectionId}`, {
      ...options,
      throwOnError: options?.throwOnError ?? true,
      method: "DELETE",
    }),
}
