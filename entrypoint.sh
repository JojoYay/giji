#!/bin/bash
# FastAPI (アップロードAPI) をバックグラウンドで起動
uvicorn upload_server:app --host 127.0.0.1 --port 8000 &

# Streamlit をバックグラウンドで起動
streamlit run app_paid.py --server.port=8501 --server.address=127.0.0.1 &

# Streamlit起動待ち
echo "Waiting for services..."
for i in $(seq 1 30); do
    if curl -s http://127.0.0.1:8501 > /dev/null 2>&1; then
        echo "Streamlit ready!"
        break
    fi
    sleep 1
done

# nginx をフォアグラウンドで起動
echo "Starting nginx..."
exec nginx -g "daemon off;"
