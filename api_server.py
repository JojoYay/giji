"""
議事録生成 API サーバー (FastAPI)
- POST /api/upload-url     GCS resumable upload URL 生成
- POST /api/checkout       Stripe Checkout セッション作成 + Firestoreジョブ登録
- POST /api/jobs/{id}/start 決済確認後に処理開始
- GET  /api/jobs/{id}      ジョブ状態ポーリング
"""

import os
import threading
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path

import stripe
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from google.cloud import firestore

# ───────── 設定 ─────────
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
PRICE_JPY = int(os.environ.get("STRIPE_PRICE_JPY", "500"))
GCS_BUCKET = os.environ.get("GCS_BUCKET", "giji-uploads-minutes")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
MODEL = "gemini-2.5-flash"

# フロントエンドのオリジン（Vercel URL + ローカル開発）
ALLOWED_ORIGINS = [
    o.strip()
    for o in os.environ.get(
        "ALLOWED_ORIGINS",
        "http://localhost:3000,http://localhost:8501",
    ).split(",")
    if o.strip()
]

app = FastAPI(title="議事録生成 API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_methods=["*"],
    allow_headers=["*"],
)

# Firestore クライアント（Cloud Run では自動認証）
_db: firestore.Client | None = None


def _get_db() -> firestore.Client:
    global _db
    if _db is None:
        project = os.environ.get("GCP_PROJECT") or os.environ.get("GOOGLE_CLOUD_PROJECT") or "giji-minutes"
        _db = firestore.Client(project=project, database="(default)")
    return _db


# ───────── /api/upload-url ─────────

@app.post("/api/upload-url")
async def create_upload_url(body: dict, request: Request):
    """ブラウザから GCS に直接アップロードするための Resumable Upload URL を返す。"""
    try:
        from gcs_upload import generate_resumable_upload_url
        filename = body.get("filename", "upload.mp4")
        content_type = body.get("content_type", "application/octet-stream")
        # リクエストの Origin ヘッダーを使う（どのフロントエンドからでも動作）
        origin = request.headers.get("origin") or os.environ.get("APP_ORIGIN", "https://giji-minutes.web.app")
        url, blob_name = generate_resumable_upload_url(filename, content_type, origin)
        return {"upload_url": url, "blob_name": blob_name}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ───────── /api/checkout ─────────

@app.post("/api/checkout")
async def create_checkout(body: dict):
    """
    Stripe Checkout セッションを作成し、Firestore にジョブを仮登録する。
    Returns: { checkout_url, job_id }
    """
    if not stripe.api_key:
        raise HTTPException(500, "Stripe API key not configured")

    job_id = uuid.uuid4().hex
    gcs_blob = body.get("gcs_blob", "")
    gcs_refs = body.get("gcs_refs", [])
    meeting_context = body.get("meeting_context", {})
    file_name = body.get("file_name", "recording.mp4")
    frontend_origin = body.get("frontend_origin", "http://localhost:3000")

    if not gcs_blob:
        raise HTTPException(400, "gcs_blob is required")

    # Firestore に仮登録（status: pending_payment）
    db = _get_db()
    db.collection("jobs").document(job_id).set({
        "status": "pending_payment",
        "job_id": job_id,
        "gcs_blob": gcs_blob,
        "gcs_refs": gcs_refs,
        "meeting_context": meeting_context,
        "file_name": file_name,
        "progress": [],
        "created_at": datetime.now(timezone.utc),
        "started_at": None,
        "completed_at": None,
        "error_message": None,
        "transcript_blob": None,
        "minutes_blob": None,
    })

    # Stripe Checkout セッション作成
    success_url = f"{frontend_origin}/success?job_id={job_id}&session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{frontend_origin}/upload?cancelled=1"

    session = stripe.checkout.Session.create(
        mode="payment",
        line_items=[{
            "price_data": {
                "currency": "jpy",
                "unit_amount": PRICE_JPY,
                "product_data": {
                    "name": "会議 文字起こし・議事録生成",
                    "description": f"ファイル: {file_name}",
                },
            },
            "quantity": 1,
        }],
        metadata={"job_id": job_id},
        success_url=success_url,
        cancel_url=cancel_url,
    )

    return {"checkout_url": session.url, "job_id": job_id}


# ───────── /api/jobs/{id}/start ─────────

@app.post("/api/jobs/{job_id}/start")
async def start_job(job_id: str, body: dict):
    """
    Stripe 決済確認後にバックグラウンド処理を開始する。
    body: { session_id }
    """
    session_id = body.get("session_id", "")
    if not session_id:
        raise HTTPException(400, "session_id is required")

    # Firestore からジョブ取得
    db = _get_db()
    doc_ref = db.collection("jobs").document(job_id)
    doc = doc_ref.get()
    if not doc.exists:
        raise HTTPException(404, "Job not found")

    job = doc.to_dict()
    if job["status"] not in ("pending_payment", "error"):
        # 既に処理中 or 完了
        return {"status": job["status"], "job_id": job_id}

    # Stripe 決済確認
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        if session.payment_status != "paid":
            raise HTTPException(402, f"Payment not completed: {session.payment_status}")
    except stripe.StripeError as e:
        raise HTTPException(400, f"Stripe error: {e}")

    # Firestore を processing に更新
    doc_ref.update({
        "status": "processing",
        "stripe_session_id": session_id,
        "started_at": datetime.now(timezone.utc),
        "error_message": None,
    })

    # バックグラウンドスレッドで処理開始
    t = threading.Thread(
        target=_run_job,
        args=(job_id, job),
        daemon=True,
    )
    t.start()

    return {"status": "processing", "job_id": job_id}


# ───────── /api/jobs/{id} ─────────

@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str):
    """ジョブ状態をポーリングする。"""
    db = _get_db()
    doc = db.collection("jobs").document(job_id).get()
    if not doc.exists:
        raise HTTPException(404, "Job not found")

    job = doc.to_dict()

    # タイムスタンプを文字列化
    def _fmt(ts):
        if ts is None:
            return None
        if hasattr(ts, "isoformat"):
            return ts.isoformat()
        return str(ts)

    # 結果ファイルの署名付きURL（完了時のみ）
    transcript_url = None
    minutes_url = None
    if job["status"] == "done":
        from gcs_upload import get_signed_url
        if job.get("transcript_blob"):
            transcript_url = get_signed_url(job["transcript_blob"])
        if job.get("minutes_blob"):
            minutes_url = get_signed_url(job["minutes_blob"])

    return {
        "job_id": job_id,
        "status": job["status"],
        "progress": job.get("progress", []),
        "created_at": _fmt(job.get("created_at")),
        "started_at": _fmt(job.get("started_at")),
        "completed_at": _fmt(job.get("completed_at")),
        "error_message": job.get("error_message"),
        "transcript_url": transcript_url,
        "minutes_url": minutes_url,
        "file_name": job.get("file_name", ""),
    }


# ───────── バックグラウンド処理 ─────────

def _run_job(job_id: str, job: dict):
    """バックグラウンドスレッドで run_pipeline() を実行し Firestore に進捗を書く。"""
    db = _get_db()
    doc_ref = db.collection("jobs").document(job_id)
    progress_log: list[dict] = []

    def on_progress(kind: str, msg: str):
        """run_pipeline の on_progress コールバック → Firestore に書き込む。"""
        entry = {
            "time": datetime.now(timezone.utc).isoformat(),
            "kind": kind,
            "message": msg,
        }
        progress_log.append(entry)
        # Firestoreを3件おきに更新（書き込み回数を節約）
        if len(progress_log) % 3 == 0 or kind == "step":
            doc_ref.update({"progress": progress_log})

    _gcs_tmp = None
    _ref_tmps = []
    success = False

    try:
        from gcs_upload import download_from_gcs, upload_result_to_gcs, delete_from_gcs
        from gemini_transcribe_v2 import run_pipeline, MeetingContext

        # GCS からダウンロード
        on_progress("step", "[前処理] GCSからファイルをダウンロード中...")
        _gcs_tmp = download_from_gcs(job["gcs_blob"])

        # 参考資料ダウンロード
        ref_paths = []
        for rb in job.get("gcs_refs", []):
            try:
                tmp = download_from_gcs(rb)
                ref_paths.append(tmp)
                _ref_tmps.append(tmp)
            except Exception as e:
                on_progress("step", f"  参考資料ダウンロード失敗: {rb}: {e}")

        # MeetingContext 構築
        ctx_data = job.get("meeting_context", {})
        ctx = MeetingContext(
            date=ctx_data.get("date", ""),
            time=ctx_data.get("time", ""),
            topic=ctx_data.get("topic", ""),
            participants=ctx_data.get("participants", ""),
            keywords=ctx_data.get("keywords", ""),
            glossary=ctx_data.get("glossary", ""),
            custom_instructions=ctx_data.get("custom_instructions", ""),
        )
        lang = ctx_data.get("lang", "ja")
        template_key = ctx_data.get("template_key", "standard")
        custom_template = ctx_data.get("custom_template", "")
        file_stem = Path(job.get("file_name", "recording")).stem

        # run_pipeline 実行
        transcript, summary, t_path, s_path, usage = run_pipeline(
            file_path=_gcs_tmp,
            api_key=GEMINI_API_KEY,
            model=MODEL,
            lang=lang,
            ctx=ctx,
            reference_files=ref_paths or None,
            template_key=template_key,
            custom_template=custom_template,
            output_dir="/tmp/output",
            output_prefix=file_stem,
            on_progress=on_progress,
        )

        # 結果を GCS に保存
        on_progress("step", "[完了] 結果をGCSに保存中...")
        transcript_blob = upload_result_to_gcs(t_path, f"results/{job_id}/{file_stem}_transcript.txt")
        minutes_blob = upload_result_to_gcs(s_path, f"results/{job_id}/{file_stem}_minutes.md")

        doc_ref.update({
            "status": "done",
            "completed_at": datetime.now(timezone.utc),
            "transcript_blob": transcript_blob,
            "minutes_blob": minutes_blob,
            "progress": progress_log,
            "usage_stats": usage if isinstance(usage, dict) else str(usage),
        })
        success = True

    except Exception as e:
        err = traceback.format_exc()
        doc_ref.update({
            "status": "error",
            "error_message": str(e),
            "error_detail": err[:2000],
            "progress": progress_log,
        })

    finally:
        # ローカル一時ファイルを削除
        import os as _os
        if _gcs_tmp and _os.path.exists(_gcs_tmp):
            try:
                _os.unlink(_gcs_tmp)
            except Exception:
                pass
        for rt in _ref_tmps:
            try:
                _os.unlink(rt)
            except Exception:
                pass

        if success:
            # GCS 入力ファイルを削除（成功時のみ）
            try:
                from gcs_upload import delete_from_gcs
                delete_from_gcs(job["gcs_blob"])
                for rb in job.get("gcs_refs", []):
                    delete_from_gcs(rb)
            except Exception:
                pass


# ───────── ヘルスチェック ─────────

@app.get("/api/health")
async def health():
    return {"status": "ok"}
