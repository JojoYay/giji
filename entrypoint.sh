#!/bin/bash

# Streamlitをバックグラウンドで起動
streamlit run app_paid.py --server.port=8501 --server.address=127.0.0.1 &

# Streamlitが起動するまで待機
echo "Waiting for Streamlit to start..."
for i in $(seq 1 30); do
    if curl -s http://127.0.0.1:8501 > /dev/null 2>&1; then
        echo "Streamlit is ready!"
        break
    fi
    sleep 1
done

# nginxをフォアグラウンドで起動（Cloud Runのメインプロセス）
echo "Starting nginx..."
exec nginx -g "daemon off;"
