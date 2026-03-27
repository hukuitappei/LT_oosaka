"use client"

import { useEffect } from "react"

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    console.error(error)
  }, [error])

  return (
    <div className="flex min-h-screen items-center justify-center bg-stone-950 px-6">
      <div className="max-w-md rounded-2xl border border-white/10 bg-white/5 p-8 text-center shadow-2xl shadow-black/20 backdrop-blur">
        <h2 className="mb-2 text-xl font-bold text-red-400">エラーが発生しました</h2>
        <p className="mb-6 text-sm text-stone-300">
          {error.message || "時間をおいて再試行してください。"}
        </p>
        <button
          onClick={reset}
          className="rounded-lg bg-sky-500 px-4 py-2 text-sm text-white hover:bg-sky-400"
        >
          再試行
        </button>
      </div>
    </div>
  )
}
