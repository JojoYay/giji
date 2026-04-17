"use client";

import { useCallback, useRef, useState } from "react";
import { getUploadUrl, uploadToGcs } from "@/lib/api";

interface FileDropZoneProps {
  accept: string;
  multiple?: boolean;
  label: string;
  sublabel?: string;
  onDone: (blobs: Array<{ blob_name: string; file_name: string; file_size: number }>) => void;
  disabled?: boolean;
}

export function FileDropZone({
  accept,
  multiple = false,
  label,
  sublabel,
  onDone,
  disabled,
}: FileDropZoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [loaded, setLoaded] = useState(0);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);

  const upload = useCallback(
    async (files: File[]) => {
      if (!files.length || disabled) return;
      setUploading(true);
      setError("");
      setDone(false);
      setProgress(0);

      try {
        const results = [];
        for (let i = 0; i < files.length; i++) {
          const file = files[i];
          const { upload_url, blob_name } = await getUploadUrl(file.name, file.type || "application/octet-stream");
          await uploadToGcs(upload_url, file, (pct, ld, tot) => {
            setProgress(pct);
            setLoaded(ld);
            setTotal(tot);
          });
          results.push({ blob_name, file_name: file.name, file_size: file.size });
        }
        setDone(true);
        onDone(results);
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "アップロードに失敗しました");
      } finally {
        setUploading(false);
      }
    },
    [disabled, onDone]
  );

  const handleFiles = (fileList: FileList | null) => {
    if (!fileList) return;
    upload(Array.from(fileList));
  };

  const onDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(true);
  };
  const onDragLeave = () => setDragging(false);
  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    handleFiles(e.dataTransfer.files);
  };

  return (
    <div className="w-full">
      <div
        onClick={() => !disabled && !uploading && inputRef.current?.click()}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        className={`border-2 border-dashed rounded-xl p-8 text-center transition-all cursor-pointer select-none
          ${dragging ? "border-red-400 bg-red-50" : "border-gray-300 hover:border-red-400 hover:bg-red-50"}
          ${disabled || uploading ? "opacity-60 cursor-not-allowed" : ""}
        `}
      >
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          multiple={multiple}
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
        />
        <div className="text-4xl mb-2">{done ? "✅" : "📁"}</div>
        <p className="font-medium text-gray-700">{label}</p>
        {sublabel && <p className="text-sm text-gray-400 mt-1">{sublabel}</p>}
        {!uploading && !done && (
          <button
            type="button"
            className="mt-4 px-5 py-2 bg-red-500 text-white rounded-lg text-sm font-semibold hover:bg-red-600 transition-colors"
          >
            ファイルを選択
          </button>
        )}
      </div>

      {uploading && (
        <div className="mt-3">
          <div className="w-full bg-gray-200 rounded-full h-6 overflow-hidden">
            <div
              className="bg-red-500 h-full rounded-full flex items-center justify-center text-white text-xs font-bold transition-all duration-300"
              style={{ width: `${progress}%` }}
            >
              {progress}%
            </div>
          </div>
          <p className="text-xs text-gray-500 mt-1 text-center">
            {(loaded / 1024 / 1024).toFixed(1)} / {(total / 1024 / 1024).toFixed(1)} MB
          </p>
        </div>
      )}

      {error && (
        <p className="mt-2 text-sm text-red-600 text-center">❌ {error}</p>
      )}
    </div>
  );
}
