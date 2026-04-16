"""
GCS アップロード用 FastAPI サーバー
Streamlit と同じコンテナ内で動作し、以下を提供:
  GET  /upload          → アップロード用HTMLページ
  POST /api/upload-url  → GCS resumable upload URL を生成
"""

import os
import json
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_HTML = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ファイルアップロード - 議事録生成</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #f5f7fa; min-height: 100vh; display: flex; align-items: center; justify-content: center; }
  .container { background: white; border-radius: 16px; padding: 40px; max-width: 600px; width: 90%; box-shadow: 0 4px 24px rgba(0,0,0,0.1); }
  h1 { font-size: 24px; margin-bottom: 8px; }
  .subtitle { color: #666; margin-bottom: 24px; font-size: 14px; }
  .drop-zone { border: 2px dashed #ccc; border-radius: 12px; padding: 40px 20px; text-align: center; cursor: pointer; transition: all 0.3s; }
  .drop-zone:hover, .drop-zone.dragover { border-color: #ff4b4b; background: #fff5f5; }
  .drop-zone p { font-size: 16px; color: #333; margin-bottom: 8px; }
  .drop-zone .formats { font-size: 12px; color: #999; }
  .drop-zone input { display: none; }
  .btn { display: inline-block; background: #ff4b4b; color: white; border: none; padding: 10px 28px; border-radius: 8px; font-size: 15px; cursor: pointer; margin-top: 12px; }
  .btn:hover { background: #e03e3e; }
  .file-info { margin-top: 16px; padding: 12px 16px; background: #f0f2f6; border-radius: 8px; font-size: 14px; }
  .progress-wrap { margin-top: 16px; display: none; }
  .progress-bar-bg { background: #e0e0e0; border-radius: 8px; height: 32px; overflow: hidden; }
  .progress-bar { background: #ff4b4b; height: 100%; width: 0%; transition: width 0.3s; border-radius: 8px; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; font-size: 14px; }
  .progress-text { color: #666; margin-top: 8px; font-size: 13px; text-align: center; }
  .done { margin-top: 16px; padding: 20px; background: #d4edda; border-radius: 8px; text-align: center; display: none; }
  .done h2 { color: #155724; font-size: 20px; margin-bottom: 8px; }
  .done p { color: #155724; font-size: 14px; }
  .done .btn { background: #28a745; margin-top: 12px; text-decoration: none; display: inline-block; }
  .error { margin-top: 16px; color: #dc3545; display: none; text-align: center; }
</style>
</head>
<body>
<div class="container">
  <h1>📝 会議 文字起こし・議事録生成</h1>
  <p class="subtitle">音声/動画ファイルをアップロードしてください</p>

  <div class="drop-zone" id="dropZone">
    <p>🎤 ファイルをドラッグ＆ドロップ</p>
    <p>または</p>
    <button class="btn" onclick="document.getElementById('fileInput').click()">ファイルを選択</button>
    <input type="file" id="fileInput" accept=".mp4,.m4a,.wav,.mp3,.webm,.ogg,.flac,.mkv,.avi,.mov" />
    <p class="formats">対応形式: MP4, M4A, WAV, MP3, WEBM, OGG, FLAC, MKV, AVI, MOV</p>
  </div>

  <div class="file-info" id="fileInfo" style="display:none;"></div>

  <div class="progress-wrap" id="progressWrap">
    <div class="progress-bar-bg">
      <div class="progress-bar" id="progressBar">0%</div>
    </div>
    <p class="progress-text" id="progressText"></p>
  </div>

  <div class="done" id="doneArea">
    <h2>✅ アップロード完了！</h2>
    <p>議事録生成ページに移動します...</p>
    <a class="btn" id="continueBtn" href="#">議事録生成ページへ →</a>
  </div>

  <p class="error" id="errorText"></p>
</div>

<script>
const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');
const fileInfo = document.getElementById('fileInfo');
const progressWrap = document.getElementById('progressWrap');
const progressBar = document.getElementById('progressBar');
const progressText = document.getElementById('progressText');
const doneArea = document.getElementById('doneArea');
const continueBtn = document.getElementById('continueBtn');
const errorText = document.getElementById('errorText');

// ドラッグ＆ドロップ
dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('dragover'); });
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
dropZone.addEventListener('drop', e => { e.preventDefault(); dropZone.classList.remove('dragover'); if (e.dataTransfer.files[0]) handleFile(e.dataTransfer.files[0]); });
fileInput.addEventListener('change', () => { if (fileInput.files[0]) handleFile(fileInput.files[0]); });

async function handleFile(file) {
  const sizeMB = (file.size / 1024 / 1024).toFixed(1);
  fileInfo.textContent = '📁 ' + file.name + ' (' + sizeMB + ' MB)';
  fileInfo.style.display = 'block';
  errorText.style.display = 'none';

  // サーバーからGCSアップロードURLを取得
  try {
    const resp = await fetch('/api/upload-url', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({filename: file.name, content_type: file.type || 'application/octet-stream'})
    });
    if (!resp.ok) throw new Error('URL生成エラー: ' + resp.status);
    const data = await resp.json();

    // GCSに直接アップロード
    uploadToGCS(file, data.upload_url, data.blob_name);
  } catch(e) {
    errorText.textContent = e.message;
    errorText.style.display = 'block';
  }
}

function uploadToGCS(file, uploadUrl, blobName) {
  progressWrap.style.display = 'block';
  dropZone.style.display = 'none';

  const xhr = new XMLHttpRequest();
  xhr.open('PUT', uploadUrl, true);
  xhr.setRequestHeader('Content-Type', file.type || 'application/octet-stream');

  xhr.upload.onprogress = function(e) {
    if (e.lengthComputable) {
      const pct = Math.round(e.loaded / e.total * 100);
      progressBar.style.width = pct + '%';
      progressBar.textContent = pct + '%';
      progressText.textContent = (e.loaded/1024/1024).toFixed(1) + ' MB / ' + (e.total/1024/1024).toFixed(1) + ' MB';
    }
  };

  xhr.onload = function() {
    if (xhr.status >= 200 && xhr.status < 400) {
      progressWrap.style.display = 'none';
      doneArea.style.display = 'block';
      // Streamlitページにblob_nameを渡してリダイレクト
      const streamlitUrl = window.location.origin + '/?gcs_blob=' + encodeURIComponent(blobName) + '&gcs_fn=' + encodeURIComponent(file.name);
      continueBtn.href = streamlitUrl;
      // 2秒後に自動リダイレクト
      setTimeout(() => { window.location.href = streamlitUrl; }, 2000);
    } else {
      errorText.textContent = 'アップロードエラー: HTTP ' + xhr.status;
      errorText.style.display = 'block';
    }
  };

  xhr.onerror = function() {
    errorText.textContent = 'ネットワークエラーが発生しました。再試行してください。';
    errorText.style.display = 'block';
  };

  xhr.send(file);
}
</script>
</body>
</html>"""


@app.get("/upload", response_class=HTMLResponse)
async def upload_page():
    """アップロード用HTMLページを返す。"""
    return UPLOAD_HTML


@app.post("/api/upload-url")
async def create_upload_url(body: dict):
    """GCS resumable upload URL を生成する。"""
    try:
        from gcs_upload import generate_resumable_upload_url
        filename = body.get("filename", "upload.mp4")
        content_type = body.get("content_type", "application/octet-stream")
        # Origin はリクエストヘッダーから取得したいが、簡易版では * を使う
        origin = os.environ.get("APP_ORIGIN", "https://giji-700896522925.asia-northeast1.run.app")
        url, blob_name = generate_resumable_upload_url(filename, content_type, origin)
        return JSONResponse({"upload_url": url, "blob_name": blob_name})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
