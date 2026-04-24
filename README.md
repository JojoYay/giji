# 📝 Meeting Transcription & Minutes Generator

Automatically transcribe meeting recordings and generate structured minutes using Google Gemini.

## Architecture

```
Browser (Next.js / Firebase Hosting)
   │
   │  (Firebase Auth ID token, Stripe Checkout)
   ▼
FastAPI on Cloud Run  ──►  Firestore (job state, user history)
   │                        GCS (audio uploads, result blobs)
   ▼
Gemini 2.5 Flash (transcription + summarization)
```

- **Frontend**: Next.js 16 (App Router) hosted on Firebase Hosting. `/api/**` is rewritten to Cloud Run, so the browser sees a single origin.
- **Backend**: FastAPI on Cloud Run. Stripe Checkout for payment, Firestore for job state, GCS for binaries.
- **Auth**: Firebase Authentication (Google + Email/Password). Anonymous use is supported but no history is saved.
- **Pipeline**: `gemini_transcribe_v2.py` — ffmpeg audio extraction → Gemini transcription → summary generation using one of several templates.

## Project layout

| Path | Purpose |
|---|---|
| `api_server.py` | FastAPI entrypoint — upload URL, checkout, job start/status, drafts, history |
| `gemini_transcribe_v2.py` | Core transcription + summarization pipeline |
| `gcs_upload.py` | GCS helpers (resumable upload URLs, signed download URLs) |
| `Dockerfile` | Cloud Run image |
| `requirements.txt` | Python deps |
| `frontend/` | Next.js app (App Router) |
| `tests/` | Pytest unit tests |
| `.github/workflows/` | CI: `deploy-api.yml`, `deploy-frontend.yml` |

## Local development

### Backend

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
cp .env.example .env     # fill in secrets
uvicorn api_server:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev              # http://localhost:3000
```

Create `frontend/.env.local` with `NEXT_PUBLIC_API_URL=http://localhost:8000` and the `NEXT_PUBLIC_FIREBASE_*` values from Firebase Console.

## Deployment

Push to `master` — GitHub Actions handles both:

- `deploy-api.yml` → Cloud Run (project `giji-minutes`, region `asia-northeast1`, service `giji-api`)
- `deploy-frontend.yml` → Firebase Hosting (project `giji-minutes`)

Required GitHub secrets:

| Secret | Purpose |
|---|---|
| `GCP_SA_KEY` | Service-account JSON for Cloud Run deploy |
| `FIREBASE_SERVICE_ACCOUNT` | Firebase Hosting deploy |
| `NEXT_PUBLIC_API_URL` | (empty string for same-origin rewrite) |
| `NEXT_PUBLIC_FIREBASE_API_KEY` | Firebase Web SDK config |
| `NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN` | idem |
| `NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET` | idem |
| `NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID` | idem |
| `NEXT_PUBLIC_FIREBASE_APP_ID` | idem |

Cloud Run reads `GEMINI_API_KEY` and `STRIPE_SECRET_KEY` from Google Secret Manager.

## Tests

```bash
pytest tests/
```
