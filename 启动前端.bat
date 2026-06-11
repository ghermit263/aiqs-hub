@echo off
cd /d "%~dp0frontend"
echo Starting AIQS Hub frontend at http://127.0.0.1:5173 ...
call npm run dev
pause
