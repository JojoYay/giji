"""
GCS Signed URL を使った大容量ファイルアップロード Streamlit コンポーネント。
Cloud Run の 32MB 制限を回避するため、ブラウザから直接 GCS にアップロードする。
"""

import streamlit as st
import streamlit.components.v1 as components

UPLOAD_HTML = """
<div id="upload-area" style="border: 2px dashed #ccc; border-radius: 12px; padding: 30px; text-align: center; font-family: sans-serif; background: #fafafa;">
    <div id="drop-zone">
        <p style="font-size: 18px; margin: 0 0 10px 0;">🎤 音声/動画ファイルをドラッグ＆ドロップ</p>
        <p style="color: #888; margin: 0 0 15px 0;">または</p>
        <input type="file" id="file-input" accept=".mp4,.m4a,.wav,.mp3,.webm,.ogg,.flac,.mkv,.avi,.mov"
               style="display: none;" />
        <button onclick="document.getElementById('file-input').click()"
                style="background: #ff4b4b; color: white; border: none; padding: 10px 30px; border-radius: 8px; font-size: 16px; cursor: pointer;">
            ファイルを選択
        </button>
        <p id="file-info" style="margin-top: 15px; color: #333;"></p>
    </div>
    <div id="progress-area" style="display: none; margin-top: 15px;">
        <div style="background: #e0e0e0; border-radius: 8px; overflow: hidden; height: 24px;">
            <div id="progress-bar" style="background: #ff4b4b; height: 100%%; width: 0%%; transition: width 0.3s; border-radius: 8px; display: flex; align-items: center; justify-content: center; color: white; font-size: 12px; font-weight: bold;">
                0%%
            </div>
        </div>
        <p id="progress-text" style="color: #666; margin-top: 8px;"></p>
    </div>
    <div id="done-area" style="display: none; margin-top: 15px;">
        <p style="color: #28a745; font-size: 18px;">✅ アップロード完了！</p>
    </div>
    <div id="error-area" style="display: none; margin-top: 15px;">
        <p id="error-text" style="color: #dc3545; font-size: 14px;"></p>
    </div>
</div>

<script>
const SIGNED_URL = "__SIGNED_URL__";
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const progressArea = document.getElementById('progress-area');
const progressBar = document.getElementById('progress-bar');
const progressText = document.getElementById('progress-text');
const doneArea = document.getElementById('done-area');
const errorArea = document.getElementById('error-area');
const errorText = document.getElementById('error-text');
const fileInfo = document.getElementById('file-info');
const uploadArea = document.getElementById('upload-area');

// ドラッグ＆ドロップ
uploadArea.addEventListener('dragover', (e) => { e.preventDefault(); uploadArea.style.borderColor = '#ff4b4b'; });
uploadArea.addEventListener('dragleave', () => { uploadArea.style.borderColor = '#ccc'; });
uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.style.borderColor = '#ccc';
    if (e.dataTransfer.files.length > 0) handleFile(e.dataTransfer.files[0]);
});

fileInput.addEventListener('change', () => {
    if (fileInput.files.length > 0) handleFile(fileInput.files[0]);
});

function handleFile(file) {
    const sizeMB = (file.size / 1024 / 1024).toFixed(1);
    fileInfo.textContent = `📁 ${file.name} (${sizeMB} MB)`;
    uploadFile(file);
}

function uploadFile(file) {
    progressArea.style.display = 'block';
    doneArea.style.display = 'none';
    errorArea.style.display = 'none';

    const xhr = new XMLHttpRequest();
    xhr.open('PUT', SIGNED_URL, true);
    xhr.setRequestHeader('Content-Type', file.type || 'application/octet-stream');

    xhr.upload.onprogress = (e) => {
        if (e.lengthComputable) {
            const pct = Math.round((e.loaded / e.total) * 100);
            progressBar.style.width = pct + '%%';
            progressBar.textContent = pct + '%%';
            const loadedMB = (e.loaded / 1024 / 1024).toFixed(1);
            const totalMB = (e.total / 1024 / 1024).toFixed(1);
            progressText.textContent = `${loadedMB} MB / ${totalMB} MB`;
        }
    };

    xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
            progressArea.style.display = 'none';
            doneArea.style.display = 'block';
            // Streamlit に完了を通知
            window.parent.postMessage({type: 'streamlit:setComponentValue', value: {
                status: 'done', filename: file.name, size: file.size
            }}, '*');
        } else {
            errorArea.style.display = 'block';
            errorText.textContent = `アップロードエラー: HTTP ${xhr.status}`;
        }
    };

    xhr.onerror = () => {
        errorArea.style.display = 'block';
        errorText.textContent = 'ネットワークエラーが発生しました。';
    };

    xhr.send(file);
}
</script>
"""


def gcs_file_uploader(signed_url: str, height: int = 220) -> dict | None:
    """GCS Signed URL を使ったファイルアップローダーを表示する。

    Returns:
        {"status": "done", "filename": "...", "size": 123} or None
    """
    html = UPLOAD_HTML.replace("__SIGNED_URL__", signed_url)
    result = components.html(html, height=height)
    return result
