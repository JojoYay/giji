FROM python:3.12-slim

WORKDIR /app

# ffmpeg + nginx + curl インストール
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg nginx curl && \
    rm -rf /var/lib/apt/lists/*

# 依存パッケージ
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーション
COPY gemini_transcribe_v2.py app_paid.py gcs_upload.py upload_server.py ./

# Streamlit設定
COPY .streamlit/config.toml .streamlit/config.toml

# nginx設定
COPY nginx.conf /etc/nginx/sites-available/default
RUN sed -i '/http {/a \    client_max_body_size 0;' /etc/nginx/nginx.conf

# 起動スクリプト
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

RUN mkdir -p /app/output

# Streamlit設定
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
ENV STREAMLIT_SERVER_MAX_UPLOAD_SIZE=2000

EXPOSE 8080

CMD ["/app/entrypoint.sh"]
