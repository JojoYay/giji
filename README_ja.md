# 📝 会議 文字起こし・議事録生成ツール

会議の録音をアップロードするだけで、Google Gemini が文字起こしと議事録を自動生成します。

## アーキテクチャ

```
ブラウザ (Next.js / Firebase Hosting)
   │
   │  Firebase Auth ID token + Stripe Checkout
   ▼
FastAPI on Cloud Run  ──►  Firestore (ジョブ状態・ユーザー履歴)
   │                        GCS (音声/動画ファイル、生成結果)
   ▼
Gemini 2.5 Flash (文字起こし + 要約)
```

- **フロントエンド**: Next.js 16 (App Router) を Firebase Hosting でホスト。`/api/**` は Cloud Run にリライトされるため、ブラウザからは同一オリジンに見えます。
- **バックエンド**: FastAPI on Cloud Run。Stripe Checkout で決済、Firestore でジョブ管理、GCS でバイナリ保存。
- **認証**: Firebase Authentication (Google / メール+パスワード)。未ログインでも利用可能ですが、その場合は履歴が残りません。
- **パイプライン**: `gemini_transcribe_v2.py` で ffmpeg による音声抽出 → Gemini で文字起こし → テンプレートに沿って議事録生成。

## ディレクトリ構成

| パス | 役割 |
|---|---|
| `api_server.py` | FastAPI 本体（アップロードURL / Checkout / ジョブ管理 / ドラフト / 履歴） |
| `gemini_transcribe_v2.py` | 文字起こし + 要約パイプライン |
| `gcs_upload.py` | GCS 操作（Resumable Upload URL、署名付きダウンロードURL） |
| `Dockerfile` | Cloud Run 用 |
| `requirements.txt` | Python 依存 |
| `frontend/` | Next.js アプリ (App Router) |
| `tests/` | pytest ユニットテスト |
| `.github/workflows/` | CI: `deploy-api.yml` / `deploy-frontend.yml` |

## ローカル開発

### バックエンド

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env   # 値を埋める
uvicorn api_server:app --reload --port 8000
```

### フロントエンド

```powershell
cd frontend
npm install
npm run dev              # http://localhost:3000
```

`frontend/.env.local` に以下を設定:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_FIREBASE_API_KEY=...
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=giji-minutes.firebaseapp.com
NEXT_PUBLIC_FIREBASE_PROJECT_ID=giji-minutes
NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=giji-minutes.firebasestorage.app
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=...
NEXT_PUBLIC_FIREBASE_APP_ID=...
```

## デプロイ

`master` に push すると GitHub Actions が両方をデプロイします:

- `deploy-api.yml` → Cloud Run (`giji-minutes` / `asia-northeast1` / `giji-api`)
- `deploy-frontend.yml` → Firebase Hosting (`giji-minutes`)

必要な GitHub Secrets:

| Secret | 用途 |
|---|---|
| `GCP_SA_KEY` | Cloud Run デプロイ用サービスアカウント JSON |
| `FIREBASE_SERVICE_ACCOUNT` | Firebase Hosting デプロイ用 |
| `NEXT_PUBLIC_API_URL` | 空文字列（同一オリジンの rewrite を使用） |
| `NEXT_PUBLIC_FIREBASE_*` | Firebase Web SDK の設定値 |

Cloud Run は `GEMINI_API_KEY` と `STRIPE_SECRET_KEY` を Secret Manager から読み込みます。

## テスト

```powershell
pytest tests/
```
