import type { Metadata } from "next"
import "./globals.css"
import NavBar from "@/components/NavBar"

export const metadata: Metadata = {
  title: "PR Knowledge Hub",
  description: "PRレビューの指摘を、次回に再利用できる学びとして蓄積するツールです。",
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
