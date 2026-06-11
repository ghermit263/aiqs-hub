@echo off
cd /d "%~dp0backend"
echo Starting AIQS Hub backend at http://127.0.0.1:8000 ...
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
pause
