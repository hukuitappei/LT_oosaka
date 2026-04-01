import type { Metadata } from "next"
import "./globals.css"
import NavBar from "@/components/NavBar"

export const metadata: Metadata = {
  title: "PR Knowledge Hub",
  description: "Turn pull request review feedback into reusable learning items and weekly digests.",
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="bg-stone-950 text-stone-100">
        <NavBar />
        <main>{children}</main>
      </body>
    </html>
  )
}
