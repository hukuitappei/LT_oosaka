"use client"

import Link from "next/link"
import { useRouter, usePathname } from "next/navigation"
import { removeToken, isAuthenticated } from "@/lib/auth"
import { useEffect, useState } from "react"

export default function NavBar() {
  const router = useRouter()
  const pathname = usePathname()
  const [authed, setAuthed] = useState(false)

  useEffect(() => {
    setAuthed(isAuthenticated())
  }, [pathname])

  if (pathname === "/login") return null

  function handleLogout() {
    removeToken()
    router.push("/login")
  }

  return (
    <nav className="bg-white border-b px-6 py-3 flex items-center justify-between">
      <div className="flex items-center gap-6">
        <Link href="/" className="font-bold text-blue-600">
          週報AI
        </Link>
        {authed && (
          <>
            <Link href="/weekly-digests" className="text-sm text-gray-600 hover:text-gray-900">
              週報
            </Link>
            <Link href="/learning-items" className="text-sm text-gray-600 hover:text-gray-900">
              学習ログ
            </Link>
          </>
        )}
      </div>
      {authed && (
        <button
          onClick={handleLogout}
          className="text-sm text-gray-500 hover:text-red-500 transition-colors"
        >
          ログアウト
        </button>
      )}
    </nav>
  )
}
