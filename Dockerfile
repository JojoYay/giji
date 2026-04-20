FROM python:3.12-slim

WORKDIR /app

# ffmpeg + curl
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg curl && \
    rm -rf /var/lib/apt/lists/*

# 依存パッケージ
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーション
COPY gemini_transcribe_v2.py api_server.py gcs_upload.py ./

RUN mkdir -p /tmp/output

EXPOSE 8000

CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8000"]
