from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import BASE_DIR, settings
from .database import Base, SessionLocal, engine
from .models import User
from .routers import auth, documents, exports, papers, questions, settings_router, tasks, users
from .security import hash_password

app = FastAPI(title=settings.app_name)

# 开发模式下前端在 5173 单独跑需要 CORS；单端口生产模式同源不需要，留着无害。
# allow_origin_regex 放开内网网段的 5173，便于他人电脑用开发模式访问。
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1|10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+|172\.\d+\.\d+\.\d+):5173",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (auth.router, documents.router, tasks.router, questions.router,
          exports.router, settings_router.router, users.router, papers.router):
    app.include_router(r, prefix="/api/v1")


@app.on_event("startup")
def init_db():
    Base.metadata.create_all(bind=engine)
    # 轻量迁移：老库 users 表补 status 列（存量用户视为已激活）
    from sqlalchemy import inspect, text
    cols = {c["name"] for c in inspect(engine).get_columns("users")}
    if "status" not in cols:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN status VARCHAR(16) DEFAULT 'active'"))
            conn.execute(text("UPDATE users SET status = 'active'"))
    qcols = {c["name"] for c in inspect(engine).get_columns("questions")}
    with engine.begin() as conn:
        if "category" not in qcols:
            conn.execute(text("ALTER TABLE questions ADD COLUMN category VARCHAR(32) DEFAULT ''"))
        if "subcategory" not in qcols:
            conn.execute(text("ALTER TABLE questions ADD COLUMN subcategory VARCHAR(32) DEFAULT ''"))
    db = SessionLocal()
    try:
        if not db.query(User).first():
            db.add(User(username="admin", password_hash=hash_password("admin123"),
                        display_name="管理员", role="admin", status="active"))
            db.commit()
    finally:
        db.close()


@app.get("/api/v1/health")
def health():
    return {"status": "ok", "app": settings.app_name}


# ---------- 单端口部署：FastAPI 直接托管打包好的前端（frontend/dist） ----------
# 构建前端（npm run build）后，整个系统只需 8000 一个端口，内网其它电脑访问
# http://<本机IP>:8000 即可，无需单独跑前端、无跨域问题。
DIST_DIR = BASE_DIR.parent / "frontend" / "dist"
if DIST_DIR.exists():
    app.mount("/assets", StaticFiles(directory=DIST_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def spa(full_path: str):
        # 命中 dist 下真实文件（favicon、vite.svg 等）则直接返回，否则回落到 SPA 首页
        candidate = DIST_DIR / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(DIST_DIR / "index.html")
