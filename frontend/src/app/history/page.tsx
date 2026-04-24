"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { listJobs, deleteJob, getJob, type JobListItem } from "@/lib/api";

const STATUS_LABEL: Record<string, { label: string; color: string }> = {
  draft: { label: "下書き", color: "bg-gray-100 text-gray-600" },
  pending_payment: { label: "未決済", color: "bg-yellow-100 text-yellow-700" },
  processing: { label: "処理中", color: "bg-blue-100 text-blue-700" },
  done: { label: "完了", color: "bg-green-100 text-green-700" },
  error: { label: "エラー", color: "bg-red-100 text-red-700" },
};

export default function HistoryPage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const [jobs, setJobs] = useState<JobListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  useEffect(() => {
    if (authLoading) return;
    if (!user) {
      router.replace("/login?next=/history");
      return;
    }
    (async () => {
      try {
        const { jobs } = await listJobs();
        setJobs(jobs);
      } catch (e: unknown) {
        setErr(e instanceof Error ? e.message : "取得失敗");
      } finally {
        setLoading(false);
      }
    })();
  }, [user, authLoading, router]);

  const handleDelete = async (id: string) => {
    if (!confirm("このジョブを削除しますか？")) return;
    try {
      await deleteJob(id);
      setJobs((prev) => prev.filter((j) => j.job_id !== id));
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : "削除失敗");
    }
  };

  const handleDownload = async (id: string) => {
    try {
      const j = await getJob(id);
      if (j.transcript_url) window.open(j.transcript_url, "_blank");
      if (j.minutes_url) setTimeout(() => window.open(j.minutes_url!, "_blank"), 400);
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : "取得失敗");
    }
  };

  if (authLoading || loading) {
    return <div className="p-8 text-center text-gray-500">読み込み中...</div>;
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4">
      <div className="max-w-3xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold">📚 履歴</h1>
          <Link
            href="/upload"
            className="bg-red-500 text-white px-4 py-2 rounded-lg text-sm hover:bg-red-600"
          >
            + 新規作成
          </Link>
        </div>

        {err && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-3 mb-4 text-sm text-red-700">
            {err}
          </div>
        )}

        {jobs.length === 0 ? (
          <div className="bg-white rounded-2xl border border-gray-100 p-10 text-center text-gray-500">
            まだジョブがありません。<br />
            <Link href="/upload" className="text-red-500 underline">
              新規作成
            </Link>
            してください。
          </div>
        ) : (
          <ul className="space-y-3">
            {jobs.map((j) => {
              const s = STATUS_LABEL[j.status] ?? { label: j.status, color: "bg-gray-100 text-gray-600" };
              const topic = j.meeting_context?.topic;
              const date = (j.updated_at || j.created_at || "").slice(0, 10);
              return (
                <li
                  key={j.job_id}
                  className="bg-white rounded-xl border border-gray-100 p-4 flex items-center justify-between gap-3"
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`text-xs px-2 py-0.5 rounded-full ${s.color}`}>{s.label}</span>
                      {j.purchased && (
                        <span className="text-xs px-2 py-0.5 rounded-full bg-indigo-100 text-indigo-700">
                          購入済
                        </span>
                      )}
                      <span className="text-xs text-gray-400">{date}</span>
                    </div>
                    <p className="text-sm font-medium truncate">
                      {topic || j.file_name || "(無題)"}
                    </p>
                    <p className="text-xs text-gray-500 truncate">{j.file_name}</p>
                    {j.error_message && (
                      <p className="text-xs text-red-500 truncate">{j.error_message}</p>
                    )}
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    {j.status === "done" && (
                      <button
                        onClick={() => handleDownload(j.job_id)}
                        className="text-xs px-3 py-1.5 bg-green-500 text-white rounded-lg hover:bg-green-600"
                      >
                        DL
                      </button>
                    )}
                    {(j.status === "draft" || j.status === "pending_payment") && (
                      <Link
                        href={`/upload?draft=${j.job_id}`}
                        className="text-xs px-3 py-1.5 bg-red-500 text-white rounded-lg hover:bg-red-600"
                      >
                        続きから
                      </Link>
                    )}
                    {j.status === "done" && (
                      <Link
                        href={`/upload`}
                        className="text-xs px-3 py-1.5 border border-gray-300 rounded-lg hover:bg-gray-50"
                      >
                        再作成
                      </Link>
                    )}
                    <button
                      onClick={() => handleDelete(j.job_id)}
                      className="text-xs text-gray-400 hover:text-red-500"
                      title="削除"
                    >
                      🗑
                    </button>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}
