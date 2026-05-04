import { getClientRequestHeaders, getToken } from "@/lib/auth"

export type LearningItemStatus = "new" | "in_progress" | "applied" | "ignored"

export interface LearningItem {
  id: number
  pull_request_id: number | null
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
  space_id?: number
  workspace_id: number
  year: number
  week: number
  summary: string
  repeated_issues: string[]
  next_time_notes: string[]
  pr_count: number
  learning_count: number
  reuse_event_count: number
  reused_learning_item_count: number
  recurring_reuse_event_count: number
  clean_reuse_event_count: number
  visibility: string
  created_at: string
}

export interface LearningItemsSummary {
  total_learning_items: number
  current_week_count: number
  total_reuse_events: number
  reused_learning_items_count: number
  current_week_reuse_count: number
  recurring_reuse_events: number
  clean_reuse_events: number
  weekly_points: Array<{
    year: number
    week: number
    label: string
    learning_count: number
  }>
  reuse_weekly_points: Array<{
    year: number
    week: number
    label: string
    reuse_count: number
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
  match_types: Array<"content_match" | "review_match" | "file_path_match">
  same_repository: boolean
  relevance_score: number
  recommendation_reasons: string[]
  reuse_count: number
  reused_in_current_pr: boolean
}

export interface LearningReuseRecord {
  source_learning_item_id: number
  target_pull_request_id: number
  reuse_count: number
  already_recorded: boolean
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
  default_space_id: number
  default_workspace_id: number
}

export interface SpaceSummary {
  id: number
  name: string
  slug: string
  is_personal: boolean
  role: string
}

export interface UserProfile {
  id: number
  email: string
  github_login: string | null
  is_active: boolean
  created_at: string
  spaces: SpaceSummary[]
  workspaces: SpaceSummary[]
}

export interface SpaceContext extends SpaceSummary {
  created_at: string
}

export interface SpaceSettings {
  workspace_id: number
  display_name: string
  description: string | null
  default_visibility: string
  active_goal: string | null
  active_focus_labels: string[]
  primary_repository_ids: number[]
}

type QueryValue = string | number | boolean | null | undefined

export interface ApiFetchOptions {
  token?: string
  headers?: HeadersInit
  throwOnError?: boolean
}

export interface ApiRequestOptions extends ApiFetchOptions {
  query?: Record<string, QueryValue>
  method?: string
  body?: BodyInit | FormData | string | object | null
}

export interface UpdateLearningItemInput {
  status?: LearningItemStatus
  visibility?: string
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

function buildUrl(path: string, query?: Record<string, QueryValue>): string {
  const url = new URL(`${getApiBaseUrl()}${path}`, "http://local")
  if (!query) {
    return url.pathname + url.search
  }

  for (const [key, value] of Object.entries(query)) {
    if (value === undefined || value === null || value === "") continue
    url.searchParams.set(key, String(value))
  }

  return url.pathname + url.search
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

  if (!headers.has("X-Space-Id") && clientHeaders["X-Space-Id"]) {
    headers.set("X-Space-Id", clientHeaders["X-Space-Id"])
  }

  if (!headers.has("X-Workspace-Id") && clientHeaders["X-Workspace-Id"]) {
    headers.set("X-Workspace-Id", clientHeaders["X-Workspace-Id"])
  }

  try {
    const hasBody = options.body !== undefined && options.body !== null
    if (hasBody && !(options.body instanceof FormData) && !headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json")
    }

    const body =
      !hasBody
        ? undefined
        : typeof options.body === "string" ||
            options.body instanceof FormData ||
            options.body instanceof URLSearchParams
          ? options.body
          : JSON.stringify(options.body)

    const res = await fetch(buildUrl(path, options.query), {
      method: options.method ?? "GET",
      cache: "no-store",
      headers,
      body,
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
      if (error instanceof Error) throw error
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
  updateLearningItem: (id: number, input: UpdateLearningItemInput, options?: ApiFetchOptions) =>
    apiRequest<LearningItem>(`/learning-items/${id}`, {
      ...options,
      method: "PATCH",
      body: input,
    }),
  getWeeklyDigests: (options?: ApiFetchOptions) =>
    apiFetch<WeeklyDigest[]>("/weekly-digests/", options),
  getWeeklyDigest: (id: number, options?: ApiFetchOptions) =>
    apiFetch<WeeklyDigest>(`/weekly-digests/${id}`, options),
  getCurrentUserProfile: (options?: ApiFetchOptions) => apiFetch<UserProfile>("/auth/me", options),
  getSpaces: (options?: ApiFetchOptions) => apiFetch<SpaceSummary[]>("/spaces/", options),
  getCurrentSpace: (options?: ApiFetchOptions) => apiFetch<SpaceContext>("/spaces/current/context", options),
  getSpaceSettings: (id: number, options?: ApiFetchOptions) =>
    apiFetch<SpaceSettings>(`/spaces/${id}/settings`, options),
  getPullRequest: (id: number, options?: ApiFetchOptions) =>
    apiFetch<PullRequestDetail>(`/pull-requests/${id}`, options),
  recordRelatedLearningReuse: (prId: number, itemId: number, options?: ApiFetchOptions) =>
    apiRequest<LearningReuseRecord>(`/pull-requests/${prId}/related-learning/${itemId}/reuse`, {
      ...options,
      method: "POST",
    }),
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
