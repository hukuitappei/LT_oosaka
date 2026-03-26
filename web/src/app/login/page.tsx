"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { login, register } from "@/lib/api"
import { setToken } from "@/lib/auth"

export default function LoginPage() {
  const router = useRouter()
  const [mode, setMode] = useState<"login" | "register">("login")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError("")
    setLoading(true)
    try {
      const res = mode === "login"
        ? await login(email, password)
        : await register(email, password)
      setToken(res.access_token)
      router.push("/")
      router.refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : "エラーが発生しました")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="bg-white rounded-xl shadow p-8 w-full max-w-sm">
        <h1 className="text-2xl font-bold text-center mb-2">週報AI</h1>
        <p className="text-gray-500 text-sm text-center mb-6">
          試行錯誤を知識に変える
        </p>

        <div className="flex rounded-lg overflow-hidden border mb-6">
          <button
            className={`flex-1 py-2 text-sm font-medium transition-colors ${
              mode === "login" ? "bg-blue-600 text-white" : "bg-white text-gray-600"
            }`}
            onClick={() => { setMode("login"); setError("") }}
          >
            ログイン
          </button>
          <button
            className={`flex-1 py-2 text-sm font-medium transition-colors ${
              mode === "register" ? "bg-blue-600 text-white" : "bg-white text-gray-600"
            }`}
            onClick={() => { setMode("register"); setError("") }}
          >
            新規登録
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              メールアドレス
            </label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="you@example.com"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              パスワード
            </label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="8文字以上"
              minLength={8}
            />
          </div>

          {error && (
            <p className="text-red-500 text-sm">{error}</p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 text-white rounded-lg py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {loading ? "処理中..." : mode === "login" ? "ログイン" : "アカウント作成"}
          </button>
        </form>
      </div>
    </div>
  )
}
