"use client";

import { useEffect, useState, useRef, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { startJob, getJob } from "@/lib/api";
import type { JobStatus } from "@/lib/api";
import { clearUploadState, saveFormState, DEFAULT_FORM } from "@/lib/store";

const POLL_INTERVAL_MS = 4000;

function SuccessContent() {
  const params = useSearchParams();
  const jobId = params.get("job_id") ?? "";
  const sessionId = params.get("session_id") ?? "";

  const [phase, setPhase] = useState<"starting" | "processing" | "done" | "error">("starting");
  const [job, setJob] = useState<JobStatus | null>(null);
  const [errorMsg, setErrorMsg] = useState("");
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!jobId || !sessionId) {
      setPhase("error");
      setErrorMsg("URLパラメータが不正です。やり直してください。");
      return;
    }

    // 処理開始リクエスト
    startJob(jobId, sessionId)
      .then(() => {
        setPhase("processing");
        // ポーリング開始
        intervalRef.current = setInterval(async () => {
          try {
            const status = await getJob(jobId);
            setJob(status);
            if (status.status === "done") {
              clearInterval(intervalRef.current!);
              setPhase("done");
              // sessionStorageをクリア
              clearUploadState();
              saveFormState(DEFAULT_FORM);
            } else if (status.status === "error") {
              clearInterval(intervalRef.current!);
              setPhase("error");
              setErrorMsg(status.error_message ?? "処理中にエラーが発生しました");
            }
          } catch {
            // ポーリングエラーは一時的なものとして無視
          }
        }, POLL_INTERVAL_MS);
      })
      .catch((e: Error) => {
        setPhase("error");
        setErrorMsg(e.message);
      });

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [jobId, sessionId]);

  // 最後のステップメッセージを取得
  const lastProgress = job?.progress?.slice(-1)[0]?.message ?? "";

  if (phase === "error") {
    return (
      <div className="min-h-screen flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-lg p-8 w-full max-w-xl text-center">
          <div className="text-5xl mb-4">❌</div>
          <h2 className="text-xl font-bold text-red-600 mb-2">エラーが発生しました</h2>
          <p className="text-gray-600 mb-2 text-sm">{errorMsg}</p>
          {job?.status === "error" && (
            <p className="text-xs text-gray-400 mb-4">
              ファイルはサーバーに保持されています。時間をおいてからリロードしてください。
            </p>
          )}
          <a
            href="/upload"
            className="inline-block px-6 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors"
          >
            最初からやり直す
          </a>
        </div>
      </div>
    );
  }

  if (phase === "done" && job) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-lg p-8 w-full max-w-xl">
          <div className="text-center mb-6">
            <div className="text-5xl mb-3">🎉</div>
            <h2 className="text-2xl font-bold text-green-600">生成完了！</h2>
            <p className="text-gray-500 text-sm mt-1">{job.file_name}</p>
          </div>

          <div className="space-y-3">
            {job.transcript_url && (
              <a
                href={job.transcript_url}
                download
                className="flex items-center justify-between w-full px-5 py-4 bg-blue-50 border border-blue-200 rounded-xl hover:bg-blue-100 transition-colors"
              >
                <div>
                  <p className="font-semibold text-blue-700">📄 文字起こし</p>
                  <p className="text-xs text-blue-500">テキストファイル (.txt)</p>
                </div>
                <span className="text-blue-600 font-bold">⬇ ダウンロード</span>
              </a>
            )}
            {job.minutes_url && (
              <a
                href={job.minutes_url}
                download
                className="flex items-center justify-between w-full px-5 py-4 bg-green-50 border border-green-200 rounded-xl hover:bg-green-100 transition-colors"
              >
                <div>
                  <p className="font-semibold text-green-700">📋 議事録</p>
                  <p className="text-xs text-green-500">Markdownファイル (.md)</p>
                </div>
                <span className="text-green-600 font-bold">⬇ ダウンロード</span>
              </a>
            )}
          </div>

          <p className="text-xs text-gray-400 text-center mt-4">
            ※ダウンロードリンクは1時間で期限切れになります
          </p>

          <div className="mt-5 text-center">
            <a href="/upload" className="text-sm text-gray-500 underline hover:text-gray-700">
              別のファイルを処理する
            </a>
          </div>
        </div>
      </div>
    );
  }

  // 処理中
  const progressList = job?.progress ?? [];
  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-lg p-8 w-full max-w-xl">
        {phase === "starting" ? (
          <div className="text-center">
            <div className="text-4xl mb-4 animate-pulse">✅</div>
            <h2 className="text-xl font-bold mb-2">決済完了！処理を開始します...</h2>
            <div className="w-8 h-8 border-4 border-red-400 border-t-transparent rounded-full animate-spin mx-auto mt-4" />
          </div>
        ) : (
          <>
            <h2 className="text-xl font-bold mb-2">⚙️ 処理中...</h2>
            <p className="text-sm text-gray-500 mb-4">
              文字起こし・議事録を生成しています。このページを開いたままにしてください。
            </p>

            {/* プログレスバー（アニメーション） */}
            <div className="w-full bg-gray-100 rounded-full h-3 overflow-hidden mb-2">
              <div className="h-full bg-red-400 rounded-full animate-pulse" style={{ width: "60%" }} />
            </div>

            {/* 最新のステータスメッセージ */}
            {lastProgress && (
              <p className="text-sm text-gray-600 bg-gray-50 rounded-lg px-3 py-2 mb-4 font-mono">
                {lastProgress}
              </p>
            )}

            {/* ログ */}
            {progressList.length > 0 && (
              <details className="mt-3">
                <summary className="text-xs text-gray-400 cursor-pointer select-none">
                  進捗ログを表示 ({progressList.length}件)
                </summary>
                <div className="mt-2 max-h-48 overflow-y-auto bg-gray-50 rounded-lg p-3 space-y-1">
                  {progressList.map((p, i) => (
                    <p key={i} className="text-xs text-gray-600 font-mono">
                      {p.message}
                    </p>
                  ))}
                </div>
              </details>
            )}

            <p className="text-xs text-gray-400 mt-4 text-center">
              ファイルサイズによって5〜20分ほどかかります
            </p>
          </>
        )}
      </div>
    </div>
  );
}

export default function SuccessPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-8 h-8 border-4 border-red-400 border-t-transparent rounded-full animate-spin" />
      </div>
    }>
      <SuccessContent />
    </Suspense>
  );
}
