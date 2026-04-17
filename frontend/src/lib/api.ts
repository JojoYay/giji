/**
 * FastAPI バックエンドへのAPIクライアント
 */

export const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface MeetingContext {
  date: string;
  time: string;
  topic: string;
  participants: string;
  keywords: string;
  glossary: string;
  custom_instructions: string;
  lang: string;
  template_key: string;
  custom_template: string;
}

export interface JobStatus {
  job_id: string;
  status: "pending_payment" | "processing" | "done" | "error";
  progress: Array<{ time: string; kind: string; message: string }>;
  created_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
  transcript_url: string | null;
  minutes_url: string | null;
  file_name: string;
}

/** GCS Resumable Upload URL を取得 */
export async function getUploadUrl(filename: string, contentType: string) {
  const res = await fetch(`${API_BASE}/api/upload-url`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ filename, content_type: contentType }),
  });
  if (!res.ok) throw new Error(`Upload URL error: ${res.status}`);
  return res.json() as Promise<{ upload_url: string; blob_name: string }>;
}

/** GCS へ XHR でアップロード（進捗コールバック付き） */
export function uploadToGcs(
  uploadUrl: string,
  file: File,
  onProgress: (pct: number, loaded: number, total: number) => void
): Promise<void> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("PUT", uploadUrl, true);
    xhr.setRequestHeader("Content-Type", file.type || "application/octet-stream");
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) onProgress(Math.round((e.loaded / e.total) * 100), e.loaded, e.total);
    };
    xhr.onload = () =>
      xhr.status >= 200 && xhr.status < 400 ? resolve() : reject(new Error(`HTTP ${xhr.status}`));
    xhr.onerror = () => reject(new Error("ネットワークエラー"));
    xhr.send(file);
  });
}

/** Stripe Checkout セッションを作成し、checkout_url と job_id を返す */
export async function createCheckout(params: {
  gcs_blob: string;
  gcs_refs: string[];
  meeting_context: MeetingContext;
  file_name: string;
}) {
  const res = await fetch(`${API_BASE}/api/checkout`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      ...params,
      frontend_origin: window.location.origin,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `Checkout error: ${res.status}`);
  }
  return res.json() as Promise<{ checkout_url: string; job_id: string }>;
}

/** Stripe 決済確認 → 処理開始 */
export async function startJob(jobId: string, sessionId: string) {
  const res = await fetch(`${API_BASE}/api/jobs/${jobId}/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `Start job error: ${res.status}`);
  }
  return res.json() as Promise<{ status: string; job_id: string }>;
}

/** ジョブ状態をポーリング */
export async function getJob(jobId: string): Promise<JobStatus> {
  const res = await fetch(`${API_BASE}/api/jobs/${jobId}`);
  if (!res.ok) throw new Error(`Job not found: ${res.status}`);
  return res.json();
}
