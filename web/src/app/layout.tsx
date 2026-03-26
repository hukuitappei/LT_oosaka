import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "週報AI",
  description: "試行錯誤を知識に変える週報AI",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ja">
      <body className="bg-gray-50 text-gray-900">{children}</body>
    </html>
  );
}
