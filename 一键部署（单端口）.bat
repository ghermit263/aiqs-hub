@echo off
chcp 65001 >nul
echo ============================================
echo  AIQS Hub - build frontend then serve on :8000
echo ============================================
cd /d "%~dp0frontend"
echo [1/2] Building frontend (npm run build) ...
call npm run build
if errorlevel 1 ( echo Build failed. & pause & exit /b 1 )
cd /d "%~dp0backend"
echo [2/2] Starting server on http://0.0.0.0:8000
echo Other PCs on the LAN: open http://YOUR-IP:8000
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
pause
