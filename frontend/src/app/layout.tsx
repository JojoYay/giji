import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "議事録生成 | 会議文字起こし自動化",
  description: "音声・動画ファイルから高精度な文字起こしと議事録を自動生成します",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ja">
      <body className="bg-gray-50 min-h-screen antialiased">{children}</body>
    </html>
  );
}
