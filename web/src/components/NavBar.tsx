"use client"

import Link from "next/link"
import { useEffect, useState } from "react"
import { usePathname, useRouter } from "next/navigation"
import { api, type SpaceSummary } from "@/lib/api"
import { getSpaceId, getUserEmail, isAuthenticated, removeSpaceId, removeToken, setSpaceId } from "@/lib/auth"

export default function NavBar() {
  const router = useRouter()
  const pathname = usePathname()
  const [authed, setAuthed] = useState(false)
  const [email, setEmail] = useState<string | null>(null)
  const [spaces, setSpaces] = useState<SpaceSummary[]>([])
  const [currentSpaceId, setCurrentSpaceId] = useState("")

  useEffect(() => {
    setAuthed(isAuthenticated())
    setEmail(getUserEmail())
    setCurrentSpaceId(getSpaceId() ?? "")
  }, [pathname])

  useEffect(() => {
    if (!authed) {
      setSpaces([])
      return
    }

    let cancelled = false
    void api.getCurrentUserProfile().then((profile) => {
      if (cancelled || !profile) return
      setSpaces(profile.spaces)
      if (!getSpaceId() && profile.spaces[0]) {
        const spaceId = String(profile.spaces[0].id)
        setSpaceId(spaceId)
        setCurrentSpaceId(spaceId)
      }
    })
    return () => {
      cancelled = true
    }
  }, [authed])

  if (pathname === "/login") return null

  function handleLogout() {
    removeToken()
    removeSpaceId()
    router.push("/login")
  }

  function handleSpaceChange(spaceId: string) {
    setSpaceId(spaceId)
    setCurrentSpaceId(spaceId)
    router.refresh()
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
            {spaces.length ? (
              <label className="flex items-center gap-2 text-sm text-stone-400">
                <span>Space</span>
                <select
                  value={currentSpaceId}
                  onChange={(event) => handleSpaceChange(event.target.value)}
                  className="rounded-lg border border-white/10 bg-black/20 px-2 py-1 text-sm text-stone-200"
                >
                  {spaces.map((space) => (
                    <option key={space.id} value={space.id}>
                      {space.name}
                    </option>
                  ))}
                </select>
              </label>
            ) : null}
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
