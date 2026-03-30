import http from "node:http"

const port = Number(process.env.MOCK_API_PORT || 4100)

const tokenResponse = {
  access_token: "e2e-token",
  token_type: "bearer",
  default_workspace_id: 1,
}

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
    workspace_id: 1,
    year: 2026,
    week: 13,
    summary: "Validation and API boundary handling improved.",
    repeated_issues: [],
    next_time_notes: ["Keep boundary validation early."],
    pr_count: 1,
    learning_count: 1,
    visibility: "workspace_shared",
    created_at: "2026-03-27T00:00:00Z",
  },
]

const learningItemsSummary = {
  total_learning_items: 1,
  current_week_count: 1,
  weekly_points: [
    {
      year: 2026,
      week: 13,
      label: "2026-W13",
      learning_count: 1,
    },
  ],
  top_categories: [
    {
      category: "design",
      count: 1,
    },
  ],
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

function sendJson(res, statusCode, payload) {
  res.writeHead(statusCode, { "Content-Type": "application/json" })
  res.end(JSON.stringify(payload))
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url ?? "/", `http://${req.headers.host}`)

  if (req.method === "GET" && url.pathname === "/health") {
    return sendJson(res, 200, { status: "ok" })
  }

  if (req.method === "POST" && url.pathname === "/auth/login") {
    return sendJson(res, 200, tokenResponse)
  }

  if (req.method === "GET" && url.pathname === "/learning-items/") {
    return sendJson(res, 200, learningItems)
  }

  if (req.method === "GET" && url.pathname === "/learning-items/summary") {
    return sendJson(res, 200, learningItemsSummary)
  }

  if (req.method === "GET" && url.pathname === "/weekly-digests/") {
    return sendJson(res, 200, weeklyDigests)
  }

  if (req.method === "GET" && url.pathname === "/weekly-digests/1") {
    return sendJson(res, 200, weeklyDigests[0])
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
