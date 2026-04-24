"use client";

import { useState, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/lib/auth";

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-gray-500">...</div>}>
      <LoginInner />
    </Suspense>
  );
}

function LoginInner() {
  const { user, loading, signInGoogle, signInEmail, signUpEmail } = useAuth();
  const router = useRouter();
  const params = useSearchParams();
  const next = params.get("next") || "/upload";

  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!loading && user) router.replace(next);
  }, [user, loading, router, next]);

  const onGoogle = async () => {
    setErr("");
    setBusy(true);
    try {
      await signInGoogle();
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "Google ログインに失敗しました");
    } finally {
      setBusy(false);
    }
  };

  const onEmail = async (e: React.FormEvent) => {
    e.preventDefault();
    setErr("");
    setBusy(true);
    try {
      if (mode === "signin") {
        await signInEmail(email, password);
      } else {
        await signUpEmail(email, password);
      }
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "認証に失敗しました");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4">
      <div className="max-w-md mx-auto bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
        <h1 className="text-2xl font-bold mb-1">
          {mode === "signin" ? "ログイン" : "新規登録"}
        </h1>
        <p className="text-sm text-gray-500 mb-6">
          ログインすると履歴が保存され、過去の議事録を再ダウンロードできます。
        </p>

        <button
          onClick={onGoogle}
          disabled={busy}
          className="w-full py-2.5 border border-gray-300 rounded-lg font-medium hover:bg-gray-50 disabled:opacity-50 mb-4"
        >
          🌐 Google でログイン
        </button>

        <div className="flex items-center gap-2 my-4 text-xs text-gray-400">
          <div className="flex-1 h-px bg-gray-200" />
          または
          <div className="flex-1 h-px bg-gray-200" />
        </div>

        <form onSubmit={onEmail} className="space-y-3">
          <div>
            <label className="text-xs text-gray-500 block mb-1">メールアドレス</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-300"
            />
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">パスワード</label>
            <input
              type="password"
              required
              minLength={6}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-300"
            />
          </div>
          {err && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-2 text-xs text-red-700">
              {err}
            </div>
          )}
          <button
            type="submit"
            disabled={busy}
            className="w-full py-2.5 bg-red-500 text-white rounded-lg font-medium hover:bg-red-600 disabled:opacity-50"
          >
            {busy ? "処理中..." : mode === "signin" ? "ログイン" : "登録"}
          </button>
        </form>

        <div className="mt-4 text-center text-xs text-gray-500">
          {mode === "signin" ? (
            <>
              アカウントがまだありませんか？{" "}
              <button onClick={() => setMode("signup")} className="text-red-500 underline">
                新規登録
              </button>
            </>
          ) : (
            <>
              既にアカウントをお持ちですか？{" "}
              <button onClick={() => setMode("signin")} className="text-red-500 underline">
                ログイン
              </button>
            </>
          )}
        </div>

        <div className="mt-6 text-center">
          <a href="/upload" className="text-xs text-gray-400 underline">
            ログインせずに使う（履歴は保存されません）
          </a>
        </div>
      </div>
    </div>
  );
}
