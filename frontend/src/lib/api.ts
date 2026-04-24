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
  status: "draft" | "pending_payment" | "processing" | "done" | "error";
  progress: Array<{ time: string; kind: string; message: string }>;
  created_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
  transcript_url: string | null;
  minutes_url: string | null;
  file_name: string;
}

export interface JobListItem {
  job_id: string;
  status: "draft" | "pending_payment" | "processing" | "done" | "error";
  purchased: boolean;
  file_name: string;
  meeting_context: Partial<MeetingContext>;
  created_at: string | null;
  updated_at: string | null;
  completed_at: string | null;
  error_message: string | null;
}

/** 現在の Firebase ID token を取得（ログインしていれば） */
function currentIdToken(): string | null {
  if (typeof window === "undefined") return null;
  return (window as unknown as { __gijiIdToken?: string }).__gijiIdToken ?? null;
}

function authHeaders(extra: Record<string, string> = {}): Record<string, string> {
  const h: Record<string, string> = { ...extra };
  const t = currentIdToken();
  if (t) h["Authorization"] = `Bearer ${t}`;
  return h;
}

/** GCS Resumable Upload URL を取得 */
export async function getUploadUrl(filename: string, contentType: string) {
  const res = await fetch(`${API_BASE}/api/upload-url`, {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
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
  draft_id?: string | null;
}) {
  const res = await fetch(`${API_BASE}/api/checkout`, {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
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
    headers: authHeaders({ "Content-Type": "application/json" }),
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
  const res = await fetch(`${API_BASE}/api/jobs/${jobId}`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`Job not found: ${res.status}`);
  return res.json();
}

/** ドラフト upsert（ログイン必須） */
export async function upsertDraft(params: {
  draft_id?: string | null;
  gcs_blob?: string;
  gcs_refs?: string[];
  meeting_context?: MeetingContext;
  file_name?: string;
}): Promise<{ draft_id: string }> {
  const res = await fetch(`${API_BASE}/api/drafts`, {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(params),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `Draft save error: ${res.status}`);
  }
  return res.json();
}

/** ユーザー自分のジョブ一覧（ログイン必須） */
export async function listJobs(): Promise<{ jobs: JobListItem[] }> {
  const res = await fetch(`${API_BASE}/api/jobs`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`List jobs error: ${res.status}`);
  return res.json();
}

/** ジョブ削除（ログイン必須） */
export async function deleteJob(jobId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/jobs/${jobId}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`Delete error: ${res.status}`);
}
