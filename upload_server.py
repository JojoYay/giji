"""
GCS アップロード用 FastAPI サーバー
  GET  /upload          → アップロード用HTMLページ
  POST /api/upload-url  → GCS resumable upload URL を生成
"""

import os
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

UPLOAD_HTML = r"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ファイルアップロード - 議事録生成</title>
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:-apple-system,BlinkMacSystemFont,sans-serif;background:#f5f7fa;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}
  .container{background:white;border-radius:16px;padding:36px;max-width:640px;width:100%;box-shadow:0 4px 24px rgba(0,0,0,0.1)}
  h1{font-size:22px;margin-bottom:6px}
  .sub{color:#666;margin-bottom:20px;font-size:13px}
  .section{margin-bottom:24px}
  .section h2{font-size:16px;margin-bottom:8px;color:#333}
  .drop{border:2px dashed #ccc;border-radius:10px;padding:28px 16px;text-align:center;cursor:pointer;transition:all .3s}
  .drop:hover,.drop.over{border-color:#ff4b4b;background:#fff5f5}
  .drop input{display:none}
  .btn{background:#ff4b4b;color:#fff;border:none;padding:9px 24px;border-radius:8px;font-size:14px;cursor:pointer;margin-top:8px}
  .btn:hover{background:#e03e3e}
  .btn-sm{font-size:12px;padding:5px 14px;margin-top:6px;background:#6c757d}
  .btn-sm:hover{background:#555}
  .info{margin-top:10px;padding:10px 14px;background:#f0f2f6;border-radius:8px;font-size:13px;display:none}
  .prog{margin-top:12px;display:none}
  .prog-bg{background:#e0e0e0;border-radius:8px;height:28px;overflow:hidden}
  .prog-bar{background:#ff4b4b;height:100%;width:0;transition:width .3s;border-radius:8px;display:flex;align-items:center;justify-content:center;color:#fff;font-weight:bold;font-size:13px}
  .prog-text{color:#666;margin-top:6px;font-size:12px;text-align:center}
  .done{margin-top:12px;padding:14px;background:#d4edda;border-radius:8px;display:none}
  .done p{color:#155724;font-size:14px}
  .err{color:#dc3545;margin-top:8px;display:none;text-align:center;font-size:13px}
  .ref-list{margin-top:8px;font-size:13px;color:#333}
  .ref-item{padding:4px 0;display:flex;align-items:center;gap:6px}
  .ref-item .check{color:#28a745}
  .next-area{margin-top:28px;text-align:center}
  .next-btn{display:inline-block;background:#28a745;color:#fff;padding:14px 40px;border-radius:10px;font-size:17px;text-decoration:none;font-weight:bold;border:none;cursor:pointer}
  .next-btn:hover{background:#218838}
  .next-btn:disabled{background:#ccc;cursor:not-allowed}
</style>
</head>
<body>
<div class="container">
  <h1>📝 会議 文字起こし・議事録生成</h1>
  <p class="sub">ファイルをアップロードしてください。すべて完了したら「次へ進む」ボタンを押してください。</p>

  <!-- ===== 音声/動画ファイル ===== -->
  <div class="section">
    <h2>🎤 音声/動画ファイル（必須）</h2>
    <div class="drop" id="mainDrop" onclick="document.getElementById('mainInput').click()">
      <p>ファイルをドラッグ＆ドロップ、または</p>
      <button class="btn" type="button">ファイルを選択</button>
      <input type="file" id="mainInput" accept=".mp4,.m4a,.wav,.mp3,.webm,.ogg,.flac,.mkv,.avi,.mov"/>
      <p style="color:#999;font-size:11px;margin-top:6px">MP4, M4A, WAV, MP3, WEBM, OGG, FLAC</p>
    </div>
    <div class="info" id="mainInfo"></div>
    <div class="prog" id="mainProg"><div class="prog-bg"><div class="prog-bar" id="mainBar">0%</div></div><p class="prog-text" id="mainText"></p></div>
    <div class="done" id="mainDone">
      <p>✅ アップロード完了</p>
      <button class="btn btn-sm" type="button" onclick="resetMain()">🔄 別のファイルに変更</button>
    </div>
    <p class="err" id="mainErr"></p>
  </div>

  <!-- ===== 参考資料 ===== -->
  <div class="section">
    <h2>📄 参考資料（任意）</h2>
    <p style="color:#888;font-size:12px;margin-bottom:8px">PDF・Word・PowerPoint等。複数選択可。文字起こし精度が向上します。</p>
    <div class="drop" id="refDrop" onclick="document.getElementById('refInput').click()">
      <p>参考資料をドラッグ＆ドロップ、または</p>
      <button class="btn" type="button" style="background:#6c757d">ファイルを選択</button>
      <input type="file" id="refInput" accept=".pdf,.txt,.docx,.pptx,.xlsx,.csv,.md" multiple/>
    </div>
    <div class="ref-list" id="refList"></div>
    <p class="err" id="refErr"></p>
  </div>

  <!-- ===== 次へ進むボタン ===== -->
  <div class="next-area">
    <button class="next-btn" id="nextBtn" disabled onclick="goNext()">
      議事録生成ページへ進む →
    </button>
    <p id="nextHint" style="color:#999;font-size:12px;margin-top:8px">音声/動画ファイルをアップロードすると有効になります</p>
  </div>
</div>

<script>
let mainBlob = null;
let mainFilename = null;
const refBlobs = [];

// --- 汎用アップロード関数 ---
async function uploadFile(file, onProgress) {
  const resp = await fetch('/api/upload-url', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({filename: file.name, content_type: file.type || 'application/octet-stream'})
  });
  if (!resp.ok) throw new Error('URL生成エラー: ' + resp.status);
  const data = await resp.json();
  if (data.error) throw new Error(data.error);

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('PUT', data.upload_url, true);
    xhr.setRequestHeader('Content-Type', file.type || 'application/octet-stream');
    xhr.upload.onprogress = onProgress;
    xhr.onload = () => (xhr.status >= 200 && xhr.status < 400) ? resolve(data.blob_name) : reject(new Error('HTTP ' + xhr.status));
    xhr.onerror = () => reject(new Error('ネットワークエラー'));
    xhr.send(file);
  });
}

// --- メインファイル ---
const mainDrop = document.getElementById('mainDrop');
const mainInput = document.getElementById('mainInput');
mainDrop.addEventListener('dragover', e => { e.preventDefault(); mainDrop.classList.add('over'); });
mainDrop.addEventListener('dragleave', () => mainDrop.classList.remove('over'));
mainDrop.addEventListener('drop', e => { e.preventDefault(); mainDrop.classList.remove('over'); if(e.dataTransfer.files[0]) handleMain(e.dataTransfer.files[0]); });
mainInput.addEventListener('change', () => { if(mainInput.files[0]) handleMain(mainInput.files[0]); });

async function handleMain(file) {
  const info = document.getElementById('mainInfo');
  const prog = document.getElementById('mainProg');
  const bar = document.getElementById('mainBar');
  const text = document.getElementById('mainText');
  const done = document.getElementById('mainDone');
  const err = document.getElementById('mainErr');

  info.textContent = '📁 ' + file.name + ' (' + (file.size/1024/1024).toFixed(1) + ' MB)';
  info.style.display = 'block';
  prog.style.display = 'block';
  done.style.display = 'none';
  err.style.display = 'none';
  mainDrop.style.display = 'none';

  try {
    mainBlob = await uploadFile(file, e => {
      if (e.lengthComputable) {
        const pct = Math.round(e.loaded / e.total * 100);
        bar.style.width = pct + '%'; bar.textContent = pct + '%';
        text.textContent = (e.loaded/1024/1024).toFixed(1) + ' / ' + (e.total/1024/1024).toFixed(1) + ' MB';
      }
    });
    mainFilename = file.name;
    prog.style.display = 'none';
    done.style.display = 'block';
    updateNextBtn();
  } catch(e) {
    err.textContent = e.message; err.style.display = 'block';
    mainDrop.style.display = 'block'; prog.style.display = 'none';
  }
}

function resetMain() {
  mainBlob = null;
  mainFilename = null;
  document.getElementById('mainDrop').style.display = 'block';
  document.getElementById('mainDone').style.display = 'none';
  document.getElementById('mainInfo').style.display = 'none';
  document.getElementById('mainInput').value = '';
  updateNextBtn();
}

// --- 参考資料 ---
const refDrop = document.getElementById('refDrop');
const refInput = document.getElementById('refInput');
refDrop.addEventListener('dragover', e => { e.preventDefault(); refDrop.classList.add('over'); });
refDrop.addEventListener('dragleave', () => refDrop.classList.remove('over'));
refDrop.addEventListener('drop', e => { e.preventDefault(); refDrop.classList.remove('over'); handleRefs(e.dataTransfer.files); });
refInput.addEventListener('change', () => { handleRefs(refInput.files); refInput.value = ''; });

async function handleRefs(files) {
  const list = document.getElementById('refList');
  for (const file of files) {
    const item = document.createElement('div');
    item.className = 'ref-item';
    item.innerHTML = '⏳ ' + file.name + ' アップロード中...';
    list.appendChild(item);
    try {
      const blob = await uploadFile(file, () => {});
      refBlobs.push(blob);
      item.innerHTML = '<span class="check">✅</span> ' + file.name;
    } catch(e) {
      item.innerHTML = '❌ ' + file.name + ' — ' + e.message;
    }
  }
}

// --- 次へ進むボタン ---
function updateNextBtn() {
  const btn = document.getElementById('nextBtn');
  const hint = document.getElementById('nextHint');
  if (mainBlob) {
    btn.disabled = false;
    hint.textContent = '準備完了！ボタンを押して議事録生成ページへ進みます。';
    hint.style.color = '#28a745';
  } else {
    btn.disabled = true;
    hint.textContent = '音声/動画ファイルをアップロードすると有効になります';
    hint.style.color = '#999';
  }
}

function goNext() {
  if (!mainBlob) return;
  let url = window.location.origin + '/?gcs_blob=' + encodeURIComponent(mainBlob) + '&gcs_fn=' + encodeURIComponent(mainFilename);
  if (refBlobs.length > 0) {
    url += '&gcs_refs=' + encodeURIComponent(refBlobs.join(','));
  }
  // 戻り時にフォーム状態を保持する state パラメータを引き継ぐ
  const params = new URLSearchParams(window.location.search);
  const state = params.get('state');
  if (state) {
    url += '&state=' + encodeURIComponent(state);
  }
  window.location.href = url;
}
</script>
</body>
</html>"""


@app.get("/upload", response_class=HTMLResponse)
async def upload_page():
    return UPLOAD_HTML


@app.post("/api/upload-url")
async def create_upload_url(body: dict):
    try:
        from gcs_upload import generate_resumable_upload_url
        filename = body.get("filename", "upload.mp4")
        content_type = body.get("content_type", "application/octet-stream")
        origin = os.environ.get("APP_ORIGIN", "https://giji-700896522925.asia-northeast1.run.app")
        url, blob_name = generate_resumable_upload_url(filename, content_type, origin)
        return JSONResponse({"upload_url": url, "blob_name": blob_name})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
