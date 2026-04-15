FROM python:3.12-slim

WORKDIR /app

# ffmpeg + nginx インストール
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg nginx && \
    rm -rf /var/lib/apt/lists/*

# 依存パッケージ
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーション
COPY gemini_transcribe_v2.py app_paid.py ./

# Streamlit設定ファイル
COPY .streamlit/config.toml .streamlit/config.toml

# nginx設定（大容量アップロード対応）
COPY nginx.conf /etc/nginx/sites-available/default

# 起動スクリプト
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# 出力ディレクトリ
RUN mkdir -p /app/output

# Streamlit設定
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
ENV STREAMLIT_SERVER_MAX_UPLOAD_SIZE=2000

EXPOSE 8080

CMD ["/app/entrypoint.sh"]
