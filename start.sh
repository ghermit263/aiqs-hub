#!/usr/bin/env bash
# 跨平台单端口启动（Mac / 麒麟 / Linux 原生部署用；Windows 用 一键部署（单端口）.bat）
# 用法: bash start.sh
set -e
cd "$(dirname "$0")"

echo "[1/2] 构建前端 (npm run build) ..."
( cd frontend && npm run build )

echo "[2/2] 启动服务 http://0.0.0.0:8000"
echo "局域网其它电脑访问: http://<本机IP>:8000"
cd backend
exec python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
