"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { login, register } from "@/lib/api"
import { removeWorkspaceId, setToken, setUserEmail, setWorkspaceId } from "@/lib/auth"

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
      const res = mode === "login" ? await login(email, password) : await register(email, password)
      setToken(res.access_token)
      setUserEmail(email)
      if (res.default_workspace_id) {
        setWorkspaceId(String(res.default_workspace_id))
      } else {
        removeWorkspaceId()
      }
      router.push("/")
      router.refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : "エラーが発生しました")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-6 py-10">
      <div className="w-full max-w-md rounded-[2rem] border border-white/10 bg-white/5 p-8 shadow-2xl shadow-black/20 backdrop-blur">
        <p className="mb-3 text-center text-xs font-semibold uppercase tracking-[0.35em] text-amber-300">
          Review Intelligence
        </p>
        <h1 className="mb-2 text-center text-3xl font-semibold text-white">PR Knowledge Hub</h1>
        <p className="mb-6 text-center text-sm leading-6 text-stone-300">
          PRレビューの指摘を、次回アクションとして蓄積する。
        </p>

        <div className="mb-6 flex overflow-hidden rounded-xl border border-white/10">
          <button
            className={`flex-1 py-2 text-sm font-medium transition-colors ${
              mode === "login" ? "bg-amber-300 text-stone-950" : "bg-transparent text-stone-300"
            }`}
            onClick={() => {
              setMode("login")
              setError("")
            }}
          >
            ログイン
          </button>
          <button
            className={`flex-1 py-2 text-sm font-medium transition-colors ${
              mode === "register" ? "bg-amber-300 text-stone-950" : "bg-transparent text-stone-300"
            }`}
            onClick={() => {
              setMode("register")
              setError("")
            }}
          >
            新規登録
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-stone-200">メールアドレス</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-xl border border-white/10 bg-black/10 px-3 py-2 text-sm text-white placeholder:text-stone-500 focus:outline-none focus:ring-2 focus:ring-amber-300"
              placeholder="you@example.com"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-stone-200">パスワード</label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-xl border border-white/10 bg-black/10 px-3 py-2 text-sm text-white placeholder:text-stone-500 focus:outline-none focus:ring-2 focus:ring-amber-300"
              placeholder="8文字以上"
              minLength={8}
            />
          </div>

          {error && <p className="text-sm text-red-400">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-xl bg-amber-300 py-2 text-sm font-medium text-stone-950 transition-colors hover:bg-amber-200 disabled:opacity-50"
          >
            {loading ? "処理中..." : mode === "login" ? "ログイン" : "アカウント作成"}
          </button>
        </form>
      </div>
    </div>
  )
}
