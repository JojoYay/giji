"""
GCS アップロードユーティリティ
Cloud Run の 32MB 制限を回避するため、ブラウザから直接 GCS にアップロード。
Resumable Upload URL をサーバーで生成し、ブラウザの XHR で直接 GCS に PUT する。
"""

import os
import uuid
import tempfile
import requests as _requests
from pathlib import Path
from google.cloud import storage
from google.auth.transport.requests import Request as AuthRequest
import google.auth

GCS_BUCKET = os.environ.get("GCS_BUCKET", "giji-uploads-geminipoc")


def _get_credentials():
    """Google Cloud 認証情報を取得。"""
    credentials, project = google.auth.default()
    credentials.refresh(AuthRequest())
    return credentials


def generate_resumable_upload_url(filename: str, content_type: str = "application/octet-stream") -> tuple[str, str]:
    """Resumable Upload URL を生成する。ブラウザから直接 GCS に PUT できる。

    Returns:
        (upload_url, blob_name)
    """
    ext = Path(filename).suffix
    blob_name = f"uploads/{uuid.uuid4().hex[:12]}{ext}"

    credentials = _get_credentials()

    # Resumable Upload を開始するPOSTリクエスト
    url = f"https://storage.googleapis.com/upload/storage/v1/b/{GCS_BUCKET}/o?uploadType=resumable&name={blob_name}"
    headers = {
        "Authorization": f"Bearer {credentials.token}",
        "Content-Type": "application/json",
        "X-Upload-Content-Type": content_type,
    }
    resp = _requests.post(url, headers=headers, json={"name": blob_name})
    resp.raise_for_status()

    # レスポンスの Location ヘッダーが resumable upload URL
    upload_url = resp.headers["Location"]
    return upload_url, blob_name


def download_from_gcs(blob_name: str) -> str:
    """GCS からファイルをダウンロードし、一時ファイルパスを返す。"""
    client = storage.Client()
    bucket = client.bucket(GCS_BUCKET)
    blob = bucket.blob(blob_name)
    ext = Path(blob_name).suffix
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext, prefix="gcs_")
    tmp.close()
    blob.download_to_filename(tmp.name)
    return tmp.name


def delete_from_gcs(blob_name: str):
    """GCS のファイルを削除する。"""
    try:
        client = storage.Client()
        bucket = client.bucket(GCS_BUCKET)
        bucket.blob(blob_name).delete()
    except Exception:
        pass
