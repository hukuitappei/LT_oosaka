import http from "node:http"

const port = Number(process.env.MOCK_API_PORT || 4100)

const tokenResponse = {
  access_token: "e2e-token",
  token_type: "bearer",
  default_space_id: 1,
  default_workspace_id: 1,
}

const emptyWorkspaceToken = "e2e-empty"

const spaces = [
  {
    id: 1,
    name: "Demo Personal Space",
    slug: "demo-personal-space",
    is_personal: true,
    role: "owner",
    created_at: "2026-03-27T00:00:00Z",
  },
]

const spaceSettings = {
  workspace_id: 1,
  display_name: "Demo Personal Space",
  description: "A space for validation improvements.",
  default_visibility: "workspace_shared",
  active_goal: "Stop repeated validation issues before review.",
  active_focus_labels: ["validation", "api-boundary"],
  primary_repository_ids: [10],
}

const repositories = [
  {
    id: 10,
    github_id: 100,
    full_name: "acme/review-hub",
    name: "review-hub",
    created_at: "2026-03-27T00:00:00Z",
  },
]

const learningItems = [
  {
    id: 1,
    pull_request_id: 42,
    title: "Validate before persistence",
    detail: "Reject malformed payloads before saving them.",
    category: "design",
    confidence: 0.9,
    action_for_next_time: "Add boundary validation in the request layer.",
    evidence: "The review pointed out missing validation.",
    status: "new",
    visibility: "workspace_shared",
    created_at: "2026-03-27T00:00:00Z",
    repository: {
      id: 10,
      full_name: "acme/review-hub",
      name: "review-hub",
    },
    pull_request: {
      id: 42,
      github_pr_number: 42,
      title: "Tighten validation",
      github_url: "https://github.com/acme/review-hub/pull/42",
    },
  },
]

const weeklyDigests = [
  {
    id: 1,
    space_id: 1,
    workspace_id: 1,
    year: 2026,
    week: 13,
    summary: "Validation and API boundary handling improved.",
    repeated_issues: ["Validation checks were missing at the request boundary."],
    next_time_notes: ["Keep boundary validation early."],
    pr_count: 1,
    learning_count: 1,
    reuse_event_count: 2,
    reused_learning_item_count: 1,
    recurring_reuse_event_count: 1,
    clean_reuse_event_count: 1,
    visibility: "workspace_shared",
    created_at: "2026-03-27T00:00:00Z",
  },
]

const pullRequestDetails = {
  42: {
    id: 42,
    github_pr_number: 42,
    title: "Tighten validation",
    state: "merged",
    author: "alice",
    github_url: "https://github.com/acme/review-hub/pull/42",
    processed: true,
    created_at: "2026-03-27T00:00:00Z",
    learning_items: learningItems,
    related_learning_items: [
      {
        id: 2,
        pull_request_id: 30,
        title: "Validate before persistence",
        detail: "Move validation into the API layer before saving records.",
        category: "design",
        confidence: 0.95,
        action_for_next_time: "Check boundary validation before storage writes.",
        evidence: "A prior review flagged missing validation before persistence.",
        status: "applied",
        visibility: "workspace_shared",
        created_at: "2026-03-20T00:00:00Z",
        repository: {
          id: 10,
          full_name: "acme/review-hub",
          name: "review-hub",
        },
        pull_request: {
          id: 30,
          github_pr_number: 30,
          title: "Previous validation fix",
          github_url: "https://github.com/acme/review-hub/pull/30",
        },
        matched_terms: ["persistence", "validation"],
        match_types: ["content_match", "review_match"],
        same_repository: true,
        relevance_score: 11,
        recommendation_reasons: [
          "Same repository context",
          "Matches the current learning category",
          "Previously marked as applied",
        ],
        reuse_count: 3,
        reused_in_current_pr: false,
      },
    ],
  },
}

let nextGitHubConnectionId = 3
const githubConnections = [
  {
    id: 1,
    provider_type: "token",
    workspace_id: 1,
    user_id: 1,
    installation_id: null,
    github_account_login: "octocat",
    label: "Personal token",
    is_active: true,
    created_at: "2026-03-27T00:00:00Z",
  },
  {
    id: 2,
    provider_type: "app",
    workspace_id: 1,
    user_id: 1,
    installation_id: 123456,
    github_account_login: "octocat",
    label: "GitHub App",
    is_active: true,
    created_at: "2026-03-27T00:00:00Z",
  },
]

async function readJsonBody(req) {
  const chunks = []
  for await (const chunk of req) {
    chunks.push(chunk)
  }
  const raw = Buffer.concat(chunks).toString("utf8")
  return raw ? JSON.parse(raw) : {}
}

async function readTextBody(req) {
  const chunks = []
  for await (const chunk of req) {
    chunks.push(chunk)
  }
  return Buffer.concat(chunks).toString("utf8")
}

function sendJson(res, statusCode, payload) {
  res.writeHead(statusCode, { "Content-Type": "application/json" })
  res.end(JSON.stringify(payload))
}

function filterLearningItems(url) {
  const q = (url.searchParams.get("q") || "").toLowerCase()
  const category = url.searchParams.get("category")
  const status = url.searchParams.get("status")
  const repositoryId = url.searchParams.get("repository_id")
  const limit = Number(url.searchParams.get("limit") || "100")

  return learningItems
    .filter((item) => {
      if (category && item.category !== category) return false
      if (status && item.status !== status) return false
      if (repositoryId && String(item.repository.id) !== repositoryId) return false
      if (
        q &&
        ![
          item.title,
          item.detail,
          item.evidence,
          item.action_for_next_time,
          item.pull_request.title,
          item.repository.full_name,
        ].some((value) => value.toLowerCase().includes(q))
      ) {
        return false
      }
      return true
    })
    .slice(0, Number.isFinite(limit) ? limit : 100)
}

function summarizeLearningItems() {
  const statusCounts = ["new", "in_progress", "applied", "ignored"].map((status) => ({
    status,
    count: learningItems.filter((item) => item.status === status).length,
  }))

  return {
    total_learning_items: learningItems.length,
    current_week_count: learningItems.length,
    total_reuse_events: 2,
    reused_learning_items_count: 1,
    current_week_reuse_count: 2,
    recurring_reuse_events: 1,
    clean_reuse_events: 1,
    weekly_points: [
      { year: 2026, week: 11, label: "2026-W11", learning_count: 0 },
      { year: 2026, week: 12, label: "2026-W12", learning_count: 0 },
      { year: 2026, week: 13, label: "2026-W13", learning_count: learningItems.length },
    ],
    reuse_weekly_points: [
      { year: 2026, week: 11, label: "2026-W11", reuse_count: 0 },
      { year: 2026, week: 12, label: "2026-W12", reuse_count: 0 },
      { year: 2026, week: 13, label: "2026-W13", reuse_count: 2 },
    ],
    top_categories: [{ category: "design", count: learningItems.length }],
    status_counts: statusCounts,
  }
}

function getBearerToken(req) {
  const header = req.headers.authorization ?? ""
  if (!header.startsWith("Bearer ")) {
    return ""
  }
  return header.slice("Bearer ".length)
}

function isEmptyWorkspaceRequest(req) {
  return getBearerToken(req) === emptyWorkspaceToken
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url ?? "/", `http://${req.headers.host}`)

  if (req.method === "GET" && url.pathname === "/health") {
    return sendJson(res, 200, { status: "ok" })
  }

  if (req.method === "POST" && url.pathname === "/auth/login") {
    const body = await readTextBody(req)
    const form = new URLSearchParams(body)
    const username = form.get("username") ?? ""
    const password = form.get("password") ?? ""
    if (username === "fail@example.com" || password === "wrong-password") {
      return sendJson(res, 401, { detail: "Invalid credentials" })
    }
    return sendJson(res, 200, tokenResponse)
  }

  if (req.method === "POST" && url.pathname === "/auth/register") {
    const body = await readJsonBody(req)
    if (!body.email || !body.password) {
      return sendJson(res, 422, { detail: "Email and password required" })
    }
    if (body.email === "taken@example.com") {
      return sendJson(res, 409, { detail: "Email already registered" })
    }
    return sendJson(res, 200, tokenResponse)
  }

  if (req.method === "GET" && url.pathname === "/auth/me") {
    return sendJson(res, 200, {
      id: 1,
      email: "e2e@example.com",
      github_login: null,
      is_active: true,
      created_at: "2026-03-27T00:00:00Z",
      spaces,
      workspaces: spaces,
    })
  }

  if (req.method === "GET" && url.pathname === "/spaces/") {
    return sendJson(res, 200, spaces)
  }

  if (req.method === "GET" && url.pathname === "/spaces/current/context") {
    return sendJson(res, 200, spaces[0])
  }

  if (req.method === "GET" && url.pathname === "/spaces/1/settings") {
    return sendJson(res, 200, spaceSettings)
  }

  if (req.method === "GET" && url.pathname === "/learning-items/summary") {
    if (isEmptyWorkspaceRequest(req)) {
      return sendJson(res, 200, {
        total_learning_items: 0,
        current_week_count: 0,
        total_reuse_events: 0,
        reused_learning_items_count: 0,
        current_week_reuse_count: 0,
        recurring_reuse_events: 0,
        clean_reuse_events: 0,
        weekly_points: [],
        reuse_weekly_points: [],
        top_categories: [],
        status_counts: [],
      })
    }
    return sendJson(res, 200, summarizeLearningItems())
  }

  if (req.method === "GET" && url.pathname === "/learning-items/") {
    if (isEmptyWorkspaceRequest(req)) {
      return sendJson(res, 200, [])
    }
    return sendJson(res, 200, filterLearningItems(url))
  }

  if (req.method === "PATCH" && url.pathname === "/learning-items/1") {
    const payload = await readJsonBody(req)
    learningItems[0] = {
      ...learningItems[0],
      ...payload,
    }
    return sendJson(res, 200, learningItems[0])
  }

  if (req.method === "GET" && url.pathname === "/repositories/") {
    return sendJson(res, 200, repositories)
  }

  if (req.method === "GET" && url.pathname === "/weekly-digests/") {
    if (isEmptyWorkspaceRequest(req)) {
      return sendJson(res, 200, [])
    }
    return sendJson(res, 200, weeklyDigests)
  }

  if (req.method === "GET" && url.pathname === "/weekly-digests/1") {
    if (isEmptyWorkspaceRequest(req)) {
      return sendJson(res, 404, { detail: "Not found" })
    }
    return sendJson(res, 200, weeklyDigests[0])
  }

  if (req.method === "GET" && url.pathname === "/pull-requests/42") {
    return sendJson(res, 200, pullRequestDetails[42])
  }

  if (req.method === "POST" && url.pathname === "/pull-requests/42/related-learning/2/reuse") {
    pullRequestDetails[42].related_learning_items[0] = {
      ...pullRequestDetails[42].related_learning_items[0],
      reuse_count: pullRequestDetails[42].related_learning_items[0].reuse_count + 1,
      reused_in_current_pr: true,
    }
    return sendJson(res, 200, {
      source_learning_item_id: 2,
      target_pull_request_id: 42,
      reuse_count: pullRequestDetails[42].related_learning_items[0].reuse_count,
      already_recorded: false,
    })
  }

  if (req.method === "GET" && url.pathname === "/github-connections/") {
    return sendJson(res, 200, githubConnections)
  }

  if (req.method === "POST" && url.pathname === "/github-connections/token") {
    const body = await readJsonBody(req)
    const connection = {
      id: nextGitHubConnectionId++,
      provider_type: "token",
      workspace_id: 1,
      user_id: 1,
      installation_id: null,
      github_account_login: body.github_account_login ?? null,
      label: body.label ?? null,
      is_active: true,
      created_at: "2026-03-30T00:00:00Z",
    }
    githubConnections.unshift(connection)
    return sendJson(res, 201, connection)
  }

  if (req.method === "POST" && url.pathname === "/github-connections/app/link") {
    const body = await readJsonBody(req)
    const existing = githubConnections.find(
      (connection) =>
        connection.provider_type === "app" &&
        connection.installation_id === body.installation_id &&
        connection.workspace_id === 1,
    )
    if (existing) {
      existing.github_account_login = body.github_account_login ?? existing.github_account_login
      existing.label = body.label ?? existing.label
      existing.is_active = true
      return sendJson(res, 201, existing)
    }
    const connection = {
      id: nextGitHubConnectionId++,
      provider_type: "app",
      workspace_id: 1,
      user_id: 1,
      installation_id: body.installation_id,
      github_account_login: body.github_account_login ?? null,
      label: body.label ?? null,
      is_active: true,
      created_at: "2026-03-30T00:00:00Z",
    }
    githubConnections.unshift(connection)
    return sendJson(res, 201, connection)
  }

  if (req.method === "DELETE" && url.pathname.startsWith("/github-connections/")) {
    const connectionId = Number(url.pathname.split("/").pop())
    const index = githubConnections.findIndex((connection) => connection.id === connectionId)
    if (index === -1) {
      return sendJson(res, 404, { detail: "Connection not found" })
    }
    githubConnections.splice(index, 1)
    return sendJson(res, 200, { status: "deleted" })
  }

  return sendJson(res, 404, { detail: "Not found" })
})

server.listen(port, "localhost", () => {
  console.log(`Mock API listening on http://localhost:${port}`)
})

function shutdown() {
  server.close(() => process.exit(0))
}

process.on("SIGINT", shutdown)
process.on("SIGTERM", shutdown)
