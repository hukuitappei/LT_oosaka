import { NextRequest, NextResponse } from "next/server"

const API_URL = process.env.API_URL || "http://localhost:8000"

type RouteContext = {
  params: Promise<{
    path: string[]
  }>
}

async function forward(request: NextRequest, context: RouteContext) {
  const { path } = await context.params
  const targetUrl = new URL(`${API_URL}/${path.join("/")}`)
  targetUrl.search = new URL(request.url).search

  const headers = new Headers(request.headers)
  headers.delete("host")
  headers.delete("connection")
  headers.delete("content-length")

  const init: RequestInit = {
    method: request.method,
    headers,
    cache: "no-store",
    redirect: "manual",
  }

  if (!["GET", "HEAD"].includes(request.method)) {
    init.body = await request.text()
  }

  try {
    const response = await fetch(targetUrl, init)
    const responseHeaders = new Headers(response.headers)
    responseHeaders.delete("content-encoding")
    responseHeaders.delete("content-length")
    return new NextResponse(response.body, {
      status: response.status,
      headers: responseHeaders,
    })
  } catch (error) {
    return NextResponse.json(
      { detail: error instanceof Error ? error.message : "Proxy request failed" },
      { status: 502 },
    )
  }
}

export async function GET(request: NextRequest, context: RouteContext) {
  return forward(request, context)
}

export async function POST(request: NextRequest, context: RouteContext) {
  return forward(request, context)
}

export async function PUT(request: NextRequest, context: RouteContext) {
  return forward(request, context)
}

export async function PATCH(request: NextRequest, context: RouteContext) {
  return forward(request, context)
}

export async function DELETE(request: NextRequest, context: RouteContext) {
  return forward(request, context)
}
