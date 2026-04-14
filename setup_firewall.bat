@echo off
echo ========================================
echo  ファイアウォール設定（管理者権限が必要）
echo ========================================
echo.
echo ポート 8501 を社内LANに公開します。
echo.

netsh advfirewall firewall add rule name="Streamlit Giji Tool" dir=in action=allow protocol=TCP localport=8501

echo.
echo 完了！ 他のPCから http://%COMPUTERNAME%:8501 でアクセスできます。
echo.
pause
