"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { FileDropZone } from "@/components/FileDropZone";
import { StepBar } from "@/components/StepBar";
import { saveUploadState, loadUploadState } from "@/lib/store";

export default function UploadPage() {
  const router = useRouter();
  const [mainBlob, setMainBlob] = useState<string | null>(null);
  const [mainName, setMainName] = useState<string | null>(null);
  const [mainSize, setMainSize] = useState<number>(0);
  const [refBlobs, setRefBlobs] = useState<string[]>([]);
  const [refNames, setRefNames] = useState<string[]>([]);

  // 戻った時に既存のアップロード状態を復元
  useEffect(() => {
    const saved = loadUploadState();
    if (saved) {
      setMainBlob(saved.gcs_blob);
      setMainName(saved.file_name);
      setMainSize(saved.file_size);
      setRefBlobs(saved.gcs_refs);
      setRefNames(saved.ref_names);
    }
  }, []);

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

  const handleNext = () => {
    if (!mainBlob || !mainName) return;
    saveUploadState({
      gcs_blob: mainBlob,
      gcs_refs: refBlobs,
      file_name: mainName,
      file_size: mainSize,
      ref_names: refNames,
    });
    router.push("/settings");
  };

  const handleReset = () => {
    setMainBlob(null);
    setMainName(null);
    setMainSize(0);
    setRefBlobs([]);
    setRefNames([]);
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-lg p-8 w-full max-w-xl">
        <h1 className="text-2xl font-bold mb-1">📝 会議 文字起こし・議事録生成</h1>
        <p className="text-sm text-gray-500 mb-6">音声/動画ファイルから議事録を自動生成します</p>

        <StepBar current={1} />

        {/* メインファイル */}
        <div className="mb-6">
          <h2 className="font-semibold text-gray-700 mb-2">🎤 音声/動画ファイル（必須）</h2>
          {mainBlob ? (
            <div className="bg-green-50 border border-green-200 rounded-xl p-4">
              <p className="text-green-700 font-medium">✅ {mainName}</p>
              <p className="text-green-600 text-sm">{(mainSize / 1024 / 1024).toFixed(1)} MB</p>
              <button
                onClick={handleReset}
                className="mt-2 text-sm text-gray-500 underline hover:text-gray-700"
              >
                🔄 別のファイルに変更
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
        <div className="mb-6">
          <h2 className="font-semibold text-gray-700 mb-1">📄 参考資料（任意）</h2>
          <p className="text-xs text-gray-400 mb-2">
            PDF・Word・PowerPoint等。複数可。文字起こし精度が向上します。
          </p>
          <FileDropZone
            accept=".pdf,.txt,.docx,.pptx,.xlsx,.csv,.md"
            multiple
            label="参考資料をドラッグ＆ドロップ"
            sublabel="PDF, Word, PowerPoint 等"
            onDone={handleRefsDone}
          />
          {refNames.length > 0 && (
            <ul className="mt-2 text-sm text-gray-600 space-y-1">
              {refNames.map((n, i) => (
                <li key={i}>✅ {n}</li>
              ))}
            </ul>
          )}
        </div>

        {/* 次へ */}
        <button
          onClick={handleNext}
          disabled={!mainBlob}
          className={`w-full py-3 rounded-xl font-bold text-lg transition-colors ${
            mainBlob
              ? "bg-green-500 text-white hover:bg-green-600"
              : "bg-gray-200 text-gray-400 cursor-not-allowed"
          }`}
        >
          会議情報を入力する →
        </button>
        {!mainBlob && (
          <p className="text-xs text-gray-400 text-center mt-2">
            音声/動画ファイルをアップロードすると有効になります
          </p>
        )}

        <div className="mt-6 border-t pt-4 text-center text-xs text-gray-400">
          Powered by Google Gemini API | 決済: Stripe
        </div>
      </div>
    </div>
  );
}
