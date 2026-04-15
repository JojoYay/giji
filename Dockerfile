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
RUN cat > /etc/nginx/sites-available/default << 'NGINX'
server {
    listen 8080;
    client_max_body_size 2G;
    proxy_read_timeout 3600;
    proxy_send_timeout 3600;
    proxy_connect_timeout 60;

    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
NGINX

# 起動スクリプト
RUN cat > /app/start.sh << 'SCRIPT'
#!/bin/bash
nginx &
exec streamlit run app_paid.py --server.port=8501 --server.address=127.0.0.1
SCRIPT
RUN chmod +x /app/start.sh

# 出力ディレクトリ
RUN mkdir -p /app/output

# Streamlit設定
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
ENV STREAMLIT_SERVER_MAX_UPLOAD_SIZE=2000

EXPOSE 8080

CMD ["/app/start.sh"]
