@echo off
chcp 65001 >nul
title 会議 文字起こし・議事録生成ツール

cd /d "%~dp0"

echo ========================================
echo   会議 文字起こし・議事録生成ツール
echo ========================================
echo.
echo ブラウザが自動で開きます。
echo 終了するにはこのウィンドウを閉じてください。
echo.

:: ローカルのみ（自分だけ使う場合）
:: C:\Python314\python.exe -m streamlit run app.py --server.headless false --browser.gatherUsageStats false

:: 社内LAN公開（同じネットワーク内の他PCからアクセス可能）
C:\Python314\python.exe -m streamlit run app.py --server.address 0.0.0.0 --server.port 8501 --server.headless true --browser.gatherUsageStats false

pause
