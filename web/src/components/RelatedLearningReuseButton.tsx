"use client"

import { startTransition, useState } from "react"
import { useRouter } from "next/navigation"
import { api } from "@/lib/api"

export function RelatedLearningReuseButton({
  prId,
  itemId,
  reusedInCurrentPr,
}: {
  prId: number
  itemId: number
  reusedInCurrentPr: boolean
}) {
  const router = useRouter()
  const [pending, setPending] = useState(false)
  const [recorded, setRecorded] = useState(reusedInCurrentPr)

  async function handleRecordReuse() {
    setPending(true)
    const result = await api.recordRelatedLearningReuse(prId, itemId)
    setPending(false)
    if (!result) return
    setRecorded(true)
    startTransition(() => {
      router.refresh()
    })
  }

  return (
    <button
      type="button"
      disabled={pending || recorded}
      onClick={() => void handleRecordReuse()}
      className="rounded-full border border-emerald-300/20 bg-emerald-300/10 px-3 py-1 text-xs text-emerald-100 disabled:cursor-not-allowed disabled:opacity-60"
    >
      {recorded ? "Reuse Recorded" : pending ? "Recording..." : "Record Reuse"}
    </button>
  )
}
