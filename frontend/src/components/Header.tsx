"use client";

import Link from "next/link";
import { useAuth } from "@/lib/auth";

export function Header() {
  const { user, loading, signOut } = useAuth();

  return (
    <header className="bg-white border-b border-gray-200">
      <div className="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between">
        <Link href="/upload" className="font-bold text-gray-800 hover:text-gray-600">
          📝 議事録生成
        </Link>
        <nav className="flex items-center gap-3 text-sm">
          <Link href="/upload" className="text-gray-600 hover:text-gray-900">
            新規作成
          </Link>
          {user && (
            <Link href="/history" className="text-gray-600 hover:text-gray-900">
              履歴
            </Link>
          )}
          {loading ? (
            <span className="text-gray-400 text-xs">...</span>
          ) : user ? (
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-500 truncate max-w-[160px]">
                {user.displayName || user.email}
              </span>
              <button
                onClick={() => signOut()}
                className="text-xs text-gray-500 underline hover:text-gray-800"
              >
                ログアウト
              </button>
            </div>
          ) : (
            <Link
              href="/login"
              className="bg-red-500 text-white px-3 py-1.5 rounded-lg text-xs hover:bg-red-600"
            >
              ログイン
            </Link>
          )}
        </nav>
      </div>
    </header>
  );
}
