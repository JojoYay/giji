"use client";

import { useState, useEffect, useRef, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { FileDropZone } from "@/components/FileDropZone";
import { saveUploadState, saveFormState, loadUploadState, loadFormState, DEFAULT_FORM } from "@/lib/store";
import { createCheckout, upsertDraft, getJob } from "@/lib/api";
import type { MeetingContext } from "@/lib/api";
import { useAuth } from "@/lib/auth";

const LANGUAGES = [
  { value: "ja", label: "日本語" },
  { value: "en", label: "English" },
  { value: "zh", label: "中文" },
  { value: "ms", label: "Bahasa Melayu" },
];

const TEMPLATES = [
  { value: "standard",      label: "標準",          desc: "アジェンダ・決定事項・アクションプランをバランスよく" },
  { value: "action_focused",label: "アクション重視", desc: "誰が・何を・いつまでを中心に整理" },
  { value: "executive",     label: "エグゼクティブ向け", desc: "1ページ以内のエグゼクティブサマリー" },
  { value: "detailed",      label: "詳細版",         desc: "発言ニュアンスも含めた詳細な記録" },
  { value: "oneonone",      label: "1on1",           desc: "目標・課題・フィードバックを整理" },
  { value: "custom",        label: "カスタム",       desc: "自由にテンプレートを編集" },
];

const PRICE_JPY = parseInt(process.env.NEXT_PUBLIC_PRICE_JPY ?? "500", 10);

export default function UploadPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-gray-500">...</div>}>
      <UploadInner />
    </Suspense>
  );
}

function UploadInner() {
  const { user } = useAuth();
  const params = useSearchParams();
  const resumeId = params.get("draft") || params.get("resume") || null;

  const [mainBlob, setMainBlob] = useState<string | null>(null);
  const [mainName, setMainName] = useState<string | null>(null);
  const [mainSize, setMainSize] = useState<number>(0);
  const [refBlobs, setRefBlobs] = useState<string[]>([]);
  const [refNames, setRefNames] = useState<string[]>([]);
  const [form, setForm] = useState<MeetingContext>(DEFAULT_FORM);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [draftId, setDraftId] = useState<string | null>(null);
  const [hydrated, setHydrated] = useState(false);

  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // 初回ハイドレーション
  useEffect(() => {
    (async () => {
      // 履歴から再開？
      if (resumeId && user) {
        try {
          const j = await getJob(resumeId);
          setMainBlob(null); // 購入済みの再生成などの場合、ファイル再アップロードが必要なので何もしない
          setForm({ ...DEFAULT_FORM, ...(j as unknown as { meeting_context?: MeetingContext }).meeting_context });
          setDraftId(resumeId);
          setHydrated(true);
          return;
        } catch {
          // fall through
        }
      }
      const up = loadUploadState();
      if (up) {
        setMainBlob(up.gcs_blob);
        setMainName(up.file_name);
        setMainSize(up.file_size);
        setRefBlobs(up.gcs_refs);
        setRefNames(up.ref_names);
      }
      setForm(loadFormState());
      setHydrated(true);
    })();
  }, [resumeId, user]);

  // ログインユーザー用：変更を debounce して Firestore に保存
  useEffect(() => {
    if (!hydrated || !user) return;
    if (!mainBlob) return; // ファイル未アップロード時は保存しない
    if (saveTimer.current) clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(async () => {
      try {
        const { draft_id } = await upsertDraft({
          draft_id: draftId,
          gcs_blob: mainBlob,
          gcs_refs: refBlobs,
          meeting_context: form,
          file_name: mainName ?? "",
        });
        if (draft_id !== draftId) setDraftId(draft_id);
      } catch (e) {
        console.warn("[draft] save failed", e);
      }
    }, 800);
    return () => {
      if (saveTimer.current) clearTimeout(saveTimer.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user, hydrated, mainBlob, mainName, refBlobs, form]);

  const set = (key: keyof MeetingContext, value: string) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  const handleMainDone = (results: Array<{ blob_name: string; file_name: string; file_size: number }>) => {
    const r = results[0];
    setMainBlob(r.blob_name);
    setMainName(r.file_name);
    setMainSize(r.file_size);
  };

  const handleRefsDone = (results: Array<{ blob_name: string; file_name: string; file_size: number }>) => {
    setRefBlobs((prev) => [...prev, ...results.map((r) => r.blob_name)]);
    setRefNames((prev) => [...prev, ...results.map((r) => r.file_name)]);
  };

  const handleReset = () => {
    setMainBlob(null); setMainName(null); setMainSize(0);
    setRefBlobs([]); setRefNames([]);
  };

  const handlePay = async () => {
    if (!mainBlob || !mainName) return;
    setLoading(true);
    setError("");
    try {
      saveUploadState({ gcs_blob: mainBlob, gcs_refs: refBlobs, file_name: mainName, file_size: mainSize, ref_names: refNames });
      saveFormState(form);
      const { checkout_url } = await createCheckout({
        gcs_blob: mainBlob,
        gcs_refs: refBlobs,
        meeting_context: form,
        file_name: mainName,
        draft_id: draftId,
      });
      window.location.href = checkout_url;
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "エラーが発生しました");
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4">
      <div className="max-w-2xl mx-auto">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold">📝 会議 文字起こし・議事録生成</h1>
          <p className="text-gray-500 mt-1">音声/動画ファイルから議事録を自動生成します</p>
          {!user && (
            <p className="text-xs text-gray-400 mt-2">
              💡 <a href="/login" className="underline">ログイン</a>すると履歴が保存されます（任意）
            </p>
          )}
        </div>

        {/* ① ファイルアップロード */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 mb-4">
          <h2 className="font-bold text-lg mb-4">① ファイルのアップロード</h2>

          {/* メインファイル */}
          <div className="mb-4">
            <p className="text-sm font-medium text-gray-600 mb-2">🎤 音声/動画ファイル（必須）</p>
            {mainBlob ? (
              <div className="bg-green-50 border border-green-200 rounded-xl p-3 flex items-center justify-between">
                <div>
                  <p className="text-green-700 font-medium text-sm">✅ {mainName}</p>
                  <p className="text-green-600 text-xs">{(mainSize / 1024 / 1024).toFixed(1)} MB</p>
                </div>
                <button onClick={handleReset} className="text-xs text-gray-400 underline hover:text-gray-600">
                  変更
                </button>
              </div>
            ) : (
              <FileDropZone
                accept=".mp4,.m4a,.wav,.mp3,.webm,.ogg,.flac,.mkv,.avi,.mov"
                label="ファイルをドラッグ＆ドロップ"
                sublabel="MP4, M4A, WAV, MP3, WEBM, OGG, FLAC 対応"
                onDone={handleMainDone}
              />
            )}
          </div>

          {/* 参考資料 */}
          <div>
            <p className="text-sm font-medium text-gray-600 mb-1">📄 参考資料（任意）</p>
            <p className="text-xs text-gray-400 mb-2">PDF・Word・PowerPoint等。複数可。文字起こし精度が向上します。</p>
            <FileDropZone
              accept=".pdf,.txt,.docx,.pptx,.xlsx,.csv,.md"
              multiple
              label="参考資料をドラッグ＆ドロップ"
              sublabel="PDF, Word, PowerPoint 等"
              onDone={handleRefsDone}
            />
            {refNames.length > 0 && (
              <ul className="mt-2 space-y-1">
                {refNames.map((n, i) => <li key={i} className="text-xs text-gray-600">✅ {n}</li>)}
              </ul>
            )}
          </div>
        </div>

        {/* ② 会議情報 */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 mb-4">
          <h2 className="font-bold text-lg mb-4">② 会議情報の入力</h2>

          <div className="grid grid-cols-2 gap-3 mb-3">
            <div>
              <label className="text-xs text-gray-500 mb-1 block">📅 日付</label>
              <input type="date" value={form.date} onChange={(e) => set("date", e.target.value)}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-300" />
            </div>
            <div>
              <label className="text-xs text-gray-500 mb-1 block">🕐 時刻</label>
              <input type="text" placeholder="例: 10:00-12:00" value={form.time} onChange={(e) => set("time", e.target.value)}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-300" />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3 mb-3">
            <div>
              <label className="text-xs text-gray-500 mb-1 block">🎯 会議テーマ</label>
              <input type="text" placeholder="例: Q2売上レビュー" value={form.topic} onChange={(e) => set("topic", e.target.value)}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-300" />
            </div>
            <div>
              <label className="text-xs text-gray-500 mb-1 block">👥 参加者</label>
              <input type="text" placeholder="例: 山田, 吉田, 渡辺" value={form.participants} onChange={(e) => set("participants", e.target.value)}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-300" />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3 mb-3">
            <div>
              <label className="text-xs text-gray-500 mb-1 block">🌐 出力言語</label>
              <select value={form.lang} onChange={(e) => set("lang", e.target.value)}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-300">
                {LANGUAGES.map((l) => <option key={l.value} value={l.value}>{l.label}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500 mb-1 block">📑 テンプレート</label>
              <select value={form.template_key} onChange={(e) => set("template_key", e.target.value)}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-300">
                {TEMPLATES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
              </select>
            </div>
          </div>

          {form.template_key === "custom" && (
            <div className="mb-3">
              <label className="text-xs text-gray-500 mb-1 block">カスタムテンプレート</label>
              <textarea placeholder="テンプレートを入力..." value={form.custom_template} onChange={(e) => set("custom_template", e.target.value)}
                rows={4} className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-300" />
            </div>
          )}

          {/* 詳細オプション */}
          <details className="group">
            <summary className="cursor-pointer text-sm text-gray-500 select-none hover:text-gray-700">
              🔧 詳細オプション（キーワード・辞書・追加指示）
            </summary>
            <div className="mt-3 space-y-3">
              <div>
                <label className="text-xs text-gray-500 mb-1 block">🏷️ 重要キーワード</label>
                <textarea placeholder="例: 住宅手当, RPA, KPI" value={form.keywords} onChange={(e) => set("keywords", e.target.value)}
                  rows={2} className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-300" />
              </div>
              <div>
                <label className="text-xs text-gray-500 mb-1 block">📖 専門用語辞書</label>
                <textarea placeholder={"例:\nRPA = Robotic Process Automation\nKPI = Key Performance Indicator"}
                  value={form.glossary} onChange={(e) => set("glossary", e.target.value)}
                  rows={3} className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-300" />
              </div>
              <div>
                <label className="text-xs text-gray-500 mb-1 block">📋 追加の要約指示</label>
                <textarea placeholder="例: ですます調 / アクションプラン詳細 / 箇条書き"
                  value={form.custom_instructions} onChange={(e) => set("custom_instructions", e.target.value)}
                  rows={2} className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-300" />
              </div>
            </div>
          </details>
        </div>

        {/* ③ お支払いボタン */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-3 mb-3 text-sm text-red-700">❌ {error}</div>
        )}

        <button
          onClick={handlePay}
          disabled={!mainBlob || loading}
          className={`w-full py-4 rounded-2xl font-bold text-xl transition-colors shadow-md ${
            mainBlob && !loading
              ? "bg-red-500 text-white hover:bg-red-600"
              : "bg-gray-200 text-gray-400 cursor-not-allowed"
          }`}
        >
          {loading ? "決済ページを準備中..." : `💳 ¥${PRICE_JPY.toLocaleString()} でお支払い・議事録生成`}
        </button>
        {!mainBlob && (
          <p className="text-xs text-gray-400 text-center mt-2">
            音声/動画ファイルをアップロードすると有効になります
          </p>
        )}

        <div className="mt-6 text-center text-xs text-gray-400">
          Powered by Google Gemini API | 決済: Stripe
        </div>
      </div>
    </div>
  );
}
