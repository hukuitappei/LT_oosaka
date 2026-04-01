import http from "node:http"

const port = Number(process.env.MOCK_API_PORT || 4100)

const tokenResponse = {
  access_token: "e2e-token",
  token_type: "bearer",
  default_workspace_id: 1,
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
    weekly_points: [
      { year: 2026, week: 11, label: "2026-W11", learning_count: 0 },
      { year: 2026, week: 12, label: "2026-W12", learning_count: 0 },
      { year: 2026, week: 13, label: "2026-W13", learning_count: learningItems.length },
    ],
    top_categories: [{ category: "design", count: learningItems.length }],
    status_counts: statusCounts,
  }
}

const server = http.createServer((req, res) => {
  const url = new URL(req.url ?? "/", `http://${req.headers.host}`)

  if (req.method === "GET" && url.pathname === "/health") {
    return sendJson(res, 200, { status: "ok" })
  }

  if (req.method === "POST" && url.pathname === "/auth/login") {
    return sendJson(res, 200, tokenResponse)
  }

  if (req.method === "GET" && url.pathname === "/learning-items/summary") {
    return sendJson(res, 200, summarizeLearningItems())
  }

  if (req.method === "GET" && url.pathname === "/learning-items/") {
    return sendJson(res, 200, filterLearningItems(url))
  }

  if (req.method === "PATCH" && url.pathname === "/learning-items/1") {
    let body = ""
    req.on("data", (chunk) => {
      body += chunk
    })
    req.on("end", () => {
      const payload = body ? JSON.parse(body) : {}
      learningItems[0] = {
        ...learningItems[0],
        ...payload,
      }
      sendJson(res, 200, learningItems[0])
    })
    return
  }

  if (req.method === "GET" && url.pathname === "/repositories/") {
    return sendJson(res, 200, repositories)
  }

  if (req.method === "GET" && url.pathname === "/weekly-digests/") {
    return sendJson(res, 200, weeklyDigests)
  }

  if (req.method === "GET" && url.pathname === "/weekly-digests/1") {
    return sendJson(res, 200, weeklyDigests[0])
  }

  return sendJson(res, 404, { detail: "Not found" })
})

server.listen(port, "127.0.0.1", () => {
  console.log(`Mock API listening on http://127.0.0.1:${port}`)
})

function shutdown() {
  server.close(() => process.exit(0))
}

process.on("SIGINT", shutdown)
process.on("SIGTERM", shutdown)
