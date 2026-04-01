"use client"

import Link from "next/link"
import { useEffect, useState } from "react"
import { usePathname, useRouter } from "next/navigation"
import { getUserEmail, isAuthenticated, removeToken, removeWorkspaceId } from "@/lib/auth"

export default function NavBar() {
  const router = useRouter()
  const pathname = usePathname()
  const [authed, setAuthed] = useState(false)
  const [email, setEmail] = useState<string | null>(null)

  useEffect(() => {
    setAuthed(isAuthenticated())
    setEmail(getUserEmail())
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
          {authed ? (
            <>
              <Link href="/weekly-digests" className="text-sm text-stone-300 transition-colors hover:text-white">
                Weekly Digests
              </Link>
              <Link href="/learning-items" className="text-sm text-stone-300 transition-colors hover:text-white">
                Learning Items
              </Link>
            </>
          ) : null}
        </div>
        {authed ? (
          <div className="flex items-center gap-3">
            {email ? <span className="text-sm text-stone-500">{email}</span> : null}
            <button
              onClick={handleLogout}
              className="text-sm text-stone-400 transition-colors hover:text-red-300"
            >
              Log Out
            </button>
          </div>
        ) : null}
      </div>
    </nav>
  )
}
