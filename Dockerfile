# ---------- 阶段1：构建前端 ----------
FROM node:20-slim AS web
WORKDIR /web
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# ---------- 阶段2：后端运行时（单端口同时托管前端）----------
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1
# rapidocr/opencv 需要的系统库
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*
WORKDIR /app/backend
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
# 前端构建产物放到 main.py 期望的位置（BASE_DIR/../frontend/dist）
COPY --from=web /web/dist /app/frontend/dist
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
