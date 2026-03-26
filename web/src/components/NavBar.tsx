"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { usePathname, useRouter } from "next/navigation"
import { isAuthenticated, removeToken, removeWorkspaceId } from "@/lib/auth"

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
    removeWorkspaceId()
    router.push("/login")
  }

  return (
    <nav className="border-b border-white/10 bg-stone-950/90 px-6 py-4 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4">
        <div className="flex items-center gap-6">
          <Link href="/" className="font-semibold uppercase tracking-[0.18em] text-amber-300">
            PR Knowledge Hub
          </Link>
          {authed && (
            <>
              <Link href="/weekly-digests" className="text-sm text-stone-300 transition-colors hover:text-white">
                Weekly Digests
              </Link>
              <Link href="/learning-items" className="text-sm text-stone-300 transition-colors hover:text-white">
                Learning Items
              </Link>
            </>
          )}
        </div>
        {authed && (
          <button
            onClick={handleLogout}
            className="text-sm text-stone-400 transition-colors hover:text-red-300"
          >
            ログアウト
          </button>
        )}
      </div>
    </nav>
  )
}
