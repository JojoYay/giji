"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { StepBar } from "@/components/StepBar";
import { loadUploadState } from "@/lib/store";
import { saveFormState, loadFormState, DEFAULT_FORM } from "@/lib/store";
import { createCheckout } from "@/lib/api";
import type { MeetingContext } from "@/lib/api";

const LANGUAGES = [
  { value: "ja", label: "日本語" },
  { value: "en", label: "English" },
  { value: "zh", label: "中文" },
  { value: "ms", label: "Bahasa Melayu" },
];

const TEMPLATES = [
  { value: "standard", label: "標準", desc: "アジェンダ・決定事項・アクションプランをバランスよく" },
  { value: "action_focused", label: "アクション重視", desc: "誰が・何を・いつまでを中心に整理" },
  { value: "executive", label: "エグゼクティブ向け", desc: "1ページ以内のエグゼクティブサマリー" },
  { value: "detailed", label: "詳細版", desc: "発言ニュアンスも含めた詳細な記録" },
  { value: "oneonone", label: "1on1", desc: "目標・課題・フィードバックを整理" },
  { value: "custom", label: "カスタム", desc: "自由にテンプレートを編集" },
];

const PRICE_JPY = parseInt(process.env.NEXT_PUBLIC_PRICE_JPY ?? "500", 10);

export default function SettingsPage() {
  const router = useRouter();
  const [form, setForm] = useState<MeetingContext>(DEFAULT_FORM);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [uploadState, setUploadState] = useState<ReturnType<typeof loadUploadState>>(null);

  useEffect(() => {
    setForm(loadFormState());
    const up = loadUploadState();
    if (!up) {
      router.replace("/upload");
    } else {
      setUploadState(up);
    }
  }, [router]);

  const set = (key: keyof MeetingContext, value: string) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const handleSubmit = async () => {
    if (!uploadState) return;
    setLoading(true);
    setError("");
    try {
      saveFormState(form);
      const { checkout_url } = await createCheckout({
        gcs_blob: uploadState.gcs_blob,
        gcs_refs: uploadState.gcs_refs,
        meeting_context: form,
        file_name: uploadState.file_name,
      });
      window.location.href = checkout_url;
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "エラーが発生しました");
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-lg p-8 w-full max-w-xl">
        <h1 className="text-2xl font-bold mb-1">📝 会議 文字起こし・議事録生成</h1>
        <p className="text-sm text-gray-500 mb-6">会議情報を入力してください</p>

        <StepBar current={2} />

        {/* アップロード済みファイル確認 */}
        {uploadState && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg px-4 py-2 mb-5 flex items-center justify-between">
            <div>
              <span className="text-blue-700 text-sm font-medium">✅ {uploadState.file_name}</span>
              {uploadState.ref_names.length > 0 && (
                <span className="text-blue-500 text-xs ml-2">
                  + 参考資料 {uploadState.ref_names.length}件
                </span>
              )}
            </div>
            <button
              onClick={() => router.push("/upload")}
              className="text-xs text-blue-500 underline hover:text-blue-700"
            >
              変更
            </button>
          </div>
        )}

        {/* 会議情報 */}
        <h2 className="font-semibold text-gray-700 mb-3">📅 会議情報</h2>
        <div className="grid grid-cols-2 gap-3 mb-3">
          <div>
            <label className="text-xs text-gray-500 mb-1 block">日付</label>
            <input
              type="date"
              value={form.date}
              onChange={(e) => set("date", e.target.value)}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-300"
            />
          </div>
          <div>
            <label className="text-xs text-gray-500 mb-1 block">時刻</label>
            <input
              type="text"
              placeholder="例: 10:00-12:00"
              value={form.time}
              onChange={(e) => set("time", e.target.value)}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-300"
            />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3 mb-3">
          <div>
            <label className="text-xs text-gray-500 mb-1 block">🎯 会議テーマ</label>
            <input
              type="text"
              placeholder="例: Q2売上レビュー"
              value={form.topic}
              onChange={(e) => set("topic", e.target.value)}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-300"
            />
          </div>
          <div>
            <label className="text-xs text-gray-500 mb-1 block">👥 参加者</label>
            <input
              type="text"
              placeholder="例: 山田, 吉田, 渡辺"
              value={form.participants}
              onChange={(e) => set("participants", e.target.value)}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-300"
            />
          </div>
        </div>

        {/* 出力言語 */}
        <div className="mb-4">
          <label className="text-xs text-gray-500 mb-1 block">🌐 出力言語</label>
          <select
            value={form.lang}
            onChange={(e) => set("lang", e.target.value)}
            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-300"
          >
            {LANGUAGES.map((l) => (
              <option key={l.value} value={l.value}>{l.label}</option>
            ))}
          </select>
        </div>

        {/* テンプレート */}
        <div className="mb-4">
          <label className="text-xs text-gray-500 mb-1 block">📑 議事録テンプレート</label>
          <select
            value={form.template_key}
            onChange={(e) => set("template_key", e.target.value)}
            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-300"
          >
            {TEMPLATES.map((t) => (
              <option key={t.value} value={t.value}>{t.label} — {t.desc}</option>
            ))}
          </select>
          {form.template_key === "custom" && (
            <textarea
              placeholder="テンプレートを入力してください..."
              value={form.custom_template}
              onChange={(e) => set("custom_template", e.target.value)}
              rows={5}
              className="w-full mt-2 border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-300"
            />
          )}
        </div>

        {/* 詳細オプション */}
        <details className="mb-5 group">
          <summary className="cursor-pointer text-sm text-gray-600 font-medium select-none">
            🔧 詳細オプション
          </summary>
          <div className="mt-3 space-y-3">
            <div>
              <label className="text-xs text-gray-500 mb-1 block">🏷️ 重要キーワード</label>
              <textarea
                placeholder="例: 住宅手当, RPA, KPI"
                value={form.keywords}
                onChange={(e) => set("keywords", e.target.value)}
                rows={2}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-300"
              />
            </div>
            <div>
              <label className="text-xs text-gray-500 mb-1 block">📖 専門用語辞書</label>
              <textarea
                placeholder={"例:\nRPA = Robotic Process Automation\nKPI = Key Performance Indicator"}
                value={form.glossary}
                onChange={(e) => set("glossary", e.target.value)}
                rows={3}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-300"
              />
            </div>
            <div>
              <label className="text-xs text-gray-500 mb-1 block">📋 追加の要約指示</label>
              <textarea
                placeholder="例: ですます調 / アクションプラン詳細 / 箇条書き"
                value={form.custom_instructions}
                onChange={(e) => set("custom_instructions", e.target.value)}
                rows={2}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-300"
              />
            </div>
          </div>
        </details>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4 text-sm text-red-700">
            ❌ {error}
          </div>
        )}

        <button
          onClick={handleSubmit}
          disabled={loading}
          className="w-full py-3 rounded-xl font-bold text-lg bg-red-500 text-white hover:bg-red-600 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
        >
          {loading ? "決済ページを準備中..." : `💳 ¥${PRICE_JPY.toLocaleString()} でお支払い`}
        </button>

        <div className="mt-4 border-t pt-4 text-center text-xs text-gray-400">
          Powered by Google Gemini API | 決済: Stripe
        </div>
      </div>
    </div>
  );
}
