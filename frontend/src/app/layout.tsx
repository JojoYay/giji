import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/lib/auth";
import { Header } from "@/components/Header";

export const metadata: Metadata = {
  metadataBase: new URL("https://minutes.jittee.com"),
  title: "議事録生成 | 会議文字起こし自動化",
  description: "音声・動画ファイルから高精度な文字起こしと議事録を自動生成します",
  openGraph: {
    title: "議事録生成 | 会議文字起こし自動化",
    description: "音声・動画ファイルから高精度な文字起こしと議事録を自動生成します",
    url: "https://minutes.jittee.com",
    siteName: "議事録生成",
    locale: "ja_JP",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ja">
      <body className="bg-gray-50 min-h-screen antialiased">
        <AuthProvider>
          <Header />
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}
