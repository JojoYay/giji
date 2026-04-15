FROM python:3.12-slim

WORKDIR /app

# ffmpeg インストール
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# 依存パッケージ
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーション
COPY gemini_transcribe_v2.py app_paid.py ./

# Streamlit設定ファイル
COPY .streamlit/config.toml .streamlit/config.toml

# 出力ディレクトリ
RUN mkdir -p /app/output

# Streamlit設定
ENV STREAMLIT_SERVER_PORT=8080
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
ENV STREAMLIT_SERVER_MAX_UPLOAD_SIZE=2000
ENV STREAMLIT_SERVER_ENABLE_WEBSOCKET_COMPRESSION=false
ENV STREAMLIT_SERVER_MAX_MESSAGE_SIZE=2000

EXPOSE 8080

CMD ["streamlit", "run", "app_paid.py", "--server.port=8080", "--server.maxUploadSize=2000", "--server.maxMessageSize=2000"]
