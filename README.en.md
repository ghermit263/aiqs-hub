# AIQS Hub — Intelligent Question-Source Center

> 中文文档见 [README.md](README.md)

A front-end system that **produces, reviews, and exports questions** for an existing
exam/paper-composition system.

**Flow:** upload material → parse into chunks (keeping source location) → AI generates
questions (pending review) → human review → approved question bank → export to Excel /
assemble exam papers (A/B versions, DOCX).

## Features

- **Material parsing**: PDF / Word(.docx) / PPT(.pptx) / Excel(.xlsx) / TXT / images
  (jpg/png via on-device RapidOCR — nothing leaves the machine)
- **AI question generation** via a pluggable `model_gateway`: `mock` (offline demo),
  `openai_compat` (OpenAI / DeepSeek / Qwen / Doubao / on-prem vLLM), or `claude`
- **Question types**: single / multiple choice, true-false, fill-in-blank, short answer, essay
- **Review workbench**: edit / approve / reject / delete with source-text side-by-side,
  full audit log, duplicate hints
- **Two-level categories** (major + optional minor), batch re-categorize
- **Excel export** to your import template; **paper assembly** with A/B shuffling
  (question order + option order), preview, per-file DOCX download
- **Roles**: uploader / reviewer / admin; self-registration with admin approval
- **Three skins**: Terminal (neon-green/charcoal), Tang-dynasty (crimson/ochre/azurite),
  Song-dynasty (celadon/rice-white/tea-brown) — one click, saved locally

## Tech stack

- Backend: Python FastAPI + SQLAlchemy, SQLite by default (set `DATABASE_URL` for PostgreSQL)
- Frontend: React + TypeScript + Vite + Ant Design
- Export: openpyxl (Excel), python-docx (papers)

## Quick start (Docker, recommended)

```bash
docker compose up -d --build
# open http://localhost:8000   (default admin / admin123 — change it!)
```

Data (DB, uploads, exports) is persisted to `./data`.

## Quick start (local, no Docker)

```bash
# backend
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# frontend (dev)
cd frontend
npm install
npm run dev          # http://localhost:5173
```

For LAN/single-port deployment, run `npm run build` in `frontend/` once, then the backend
alone serves everything on port 8000 (it auto-mounts `frontend/dist`).

## Configuration

Copy `backend/.env.example` to `backend/.env`. Key vars: `JWT_SECRET`, `DATABASE_URL`,
`LLM_PROVIDER/LLM_BASE_URL/LLM_API_KEY/LLM_MODEL`, `INTRANET_ONLY`,
`CATEGORIES`, `SUBCATEGORIES_JSON`. The model can also be configured in the in-app
Settings page (overrides env).

## License

MIT — see [LICENSE](LICENSE).
