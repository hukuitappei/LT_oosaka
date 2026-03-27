import type { Metadata } from "next"
import "./globals.css"
import NavBar from "@/components/NavBar"

export const metadata: Metadata = {
  title: "PR Knowledge Hub",
  description: "PRレビューの学びを週次で蓄積し、再利用できる知識として整理するツールです。",
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="ja">
      <body className="bg-stone-950 text-stone-100">
        <NavBar />
        <main>{children}</main>
      </body>
    </html>
  )
}
