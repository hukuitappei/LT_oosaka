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
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="bg-white rounded-xl shadow p-8 max-w-md text-center">
        <h2 className="text-xl font-bold text-red-600 mb-2">エラーが発生しました</h2>
        <p className="text-gray-500 text-sm mb-6">{error.message || "予期せぬエラーです"}</p>
        <button
          onClick={reset}
          className="bg-blue-600 text-white rounded-lg px-4 py-2 text-sm hover:bg-blue-700"
        >
          再試行
        </button>
      </div>
    </div>
  )
}
