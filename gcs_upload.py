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

GCS_BUCKET = os.environ.get("GCS_BUCKET", "giji-uploads-minutes")


def _get_credentials():
    """Google Cloud 認証情報を取得。"""
    credentials, project = google.auth.default()
    credentials.refresh(AuthRequest())
    return credentials


def generate_resumable_upload_url(filename: str, content_type: str = "application/octet-stream",
                                   origin: str = "*") -> tuple[str, str]:
    """Resumable Upload URL を生成する。ブラウザから直接 GCS に PUT できる。

    Args:
        origin: CORSのOriginヘッダー（Cloud RunのURL等）

    Returns:
        (upload_url, blob_name)
    """
    ext = Path(filename).suffix
    blob_name = f"uploads/{uuid.uuid4().hex[:12]}{ext}"

    credentials = _get_credentials()

    # Resumable Upload を開始するPOSTリクエスト
    # Origin ヘッダーが必須 — これがないとGCSがCORSレスポンスを返さない
    url = f"https://storage.googleapis.com/upload/storage/v1/b/{GCS_BUCKET}/o?uploadType=resumable&name={blob_name}"
    headers = {
        "Authorization": f"Bearer {credentials.token}",
        "Content-Type": "application/json",
        "X-Upload-Content-Type": content_type,
        "Origin": origin,
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


def blob_exists(blob_name: str) -> bool:
    """GCS にファイルが存在するか確認する。"""
    try:
        client = storage.Client()
        bucket = client.bucket(GCS_BUCKET)
        return bucket.blob(blob_name).exists()
    except Exception:
        return False


def delete_from_gcs(blob_name: str):
    """GCS のファイルを削除する。"""
    try:
        client = storage.Client()
        bucket = client.bucket(GCS_BUCKET)
        bucket.blob(blob_name).delete()
    except Exception:
        pass


def upload_result_to_gcs(local_path: str, blob_name: str) -> str:
    """ローカルファイルを GCS にアップロードし、blob_name を返す。"""
    client = storage.Client()
    bucket = client.bucket(GCS_BUCKET)
    blob = bucket.blob(blob_name)
    ext = Path(blob_name).suffix.lower()
    content_type = {
        ".txt": "text/plain; charset=utf-8",
        ".md": "text/markdown; charset=utf-8",
    }.get(ext)
    if content_type:
        blob.upload_from_filename(local_path, content_type=content_type)
    else:
        blob.upload_from_filename(local_path)
    return blob_name


def get_signed_url(
    blob_name: str,
    expiration_minutes: int = 60,
    download_filename: str | None = None,
    content_type: str | None = None,
) -> str:
    """GCS blob の署名付きダウンロード URL を生成する（有効期限60分）。

    Cloud Run の Compute SA は秘密鍵を持たないため、IAM signBlob API 経由で
    署名する（service_account_email + access_token を渡す）。

    download_filename を指定すると Content-Disposition: attachment でダウンロード
    される。content_type は charset=utf-8 付きで強制設定する。
    """
    import datetime
    from urllib.parse import quote

    credentials, _ = google.auth.default()
    credentials.refresh(AuthRequest())

    service_account_email = getattr(credentials, "service_account_email", None)
    if not service_account_email or service_account_email == "default":
        try:
            md = _requests.get(
                "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/email",
                headers={"Metadata-Flavor": "Google"}, timeout=2,
            )
            service_account_email = md.text.strip()
        except Exception:
            pass

    response_type = content_type
    if response_type and "charset" not in response_type.lower():
        response_type = f"{response_type}; charset=utf-8"

    response_disposition = None
    if download_filename:
        # RFC 5987 形式で非 ASCII ファイル名に対応
        encoded = quote(download_filename, safe="")
        response_disposition = (
            f"attachment; filename=\"{download_filename}\"; "
            f"filename*=UTF-8''{encoded}"
        )

    client = storage.Client()
    bucket = client.bucket(GCS_BUCKET)
    blob = bucket.blob(blob_name)
    kwargs: dict = dict(
        expiration=datetime.timedelta(minutes=expiration_minutes),
        method="GET",
        version="v4",
        service_account_email=service_account_email,
        access_token=credentials.token,
    )
    if response_type:
        kwargs["response_type"] = response_type
    if response_disposition:
        kwargs["response_disposition"] = response_disposition

    return blob.generate_signed_url(**kwargs)
