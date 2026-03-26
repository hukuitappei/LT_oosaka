import { NextResponse } from "next/server";

export async function GET() {
  try {
    const apiUrl = process.env.API_URL || "http://localhost:8000";
    const res = await fetch(`${apiUrl}/health`, { cache: "no-store" });
    const data = await res.json();
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json(
      { status: "error", message: String(error) },
      { status: 502 }
    );
  }
}
