import time

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..llm.gateway import PROVIDERS, build_provider, get_effective_config
from ..logger import LOG_FILE, logger
from ..models import AppSetting, Document, LlmCallLog, Question, User
from ..schemas import CATEGORIES, SUBCATEGORY_SUGGESTIONS, ModelSettingsIn
from ..security import get_current_user, require_admin

router = APIRouter(tags=["settings"])


@router.get("/settings/models")
def get_model_settings(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    cfg = get_effective_config(db)
    if cfg.get("llm_api_key"):
        cfg["llm_api_key"] = cfg["llm_api_key"][:6] + "****"  # 不回传完整密钥
    cfg["providers"] = list(PROVIDERS)
    return cfg


@router.put("/settings/models")
def update_model_settings(body: ModelSettingsIn, db: Session = Depends(get_db),
                          user: User = Depends(require_admin)):
    values = body.model_dump()
    for key, value in values.items():
        if key == "llm_api_key" and (not value or value.endswith("****")):
            continue  # 留空或掩码值表示不修改密钥
        row = db.get(AppSetting, key)
        sval = str(value).lower() if isinstance(value, bool) else str(value)
        if row:
            row.value = sval
        else:
            db.add(AppSetting(key=key, value=sval))
    db.commit()
    return {"ok": True}


@router.post("/settings/models/test")
def test_model(db: Session = Depends(get_db), user: User = Depends(require_admin)):
    """用当前已保存的配置发一次最小调用，验证连通性（先保存再测试）。"""
    try:
        provider = build_provider(db)
        start = time.monotonic()
        text, _ = provider.complete("你是连通性测试助手。", "请只回复两个字：正常")
        latency = int((time.monotonic() - start) * 1000)
        logger.info("模型连接测试成功 provider=%s model=%s 耗时=%sms", provider.name, provider.model, latency)
        return {"ok": True, "latency_ms": latency,
                "reply": text[:50], "provider": provider.name, "model": provider.model}
    except Exception as e:  # noqa: BLE001
        logger.error("模型连接测试失败: %s", str(e)[:500])
        return {"ok": False, "error": str(e)[:800]}


@router.get("/settings/llm-logs")
def llm_logs(limit: int = 50, db: Session = Depends(get_db), user: User = Depends(require_admin)):
    rows = (db.query(LlmCallLog).order_by(LlmCallLog.id.desc()).limit(min(limit, 200)).all())
    return [{"id": r.id, "task_id": r.task_id, "provider": r.provider, "model": r.model,
             "latency_ms": r.latency_ms, "success": r.success,
             "prompt_tokens": r.prompt_tokens, "completion_tokens": r.completion_tokens,
             "error_msg": r.error_msg, "created_at": r.created_at} for r in rows]


@router.get("/settings/app-log")
def app_log(lines: int = 200, user: User = Depends(require_admin)):
    """返回运行日志末尾若干行（backend/logs/app.log）。"""
    if not LOG_FILE.exists():
        return {"lines": []}
    content = LOG_FILE.read_text(encoding="utf-8", errors="replace").splitlines()
    return {"lines": content[-min(lines, 1000):], "file": str(LOG_FILE)}


class ThemeIn(BaseModel):
    skin: str


@router.get("/settings/theme")
def get_theme(db: Session = Depends(get_db)):
    """机构默认皮肤（未登录也可读，供登录页应用）。本地 localStorage 优先。"""
    row = db.get(AppSetting, "ui_skin")
    return {"skin": row.value if row else "song"}


@router.put("/settings/theme")
def set_theme(body: ThemeIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if body.skin not in ("terminal", "tang", "song"):
        raise HTTPException(400, "未知主题")
    row = db.get(AppSetting, "ui_skin")
    if row:
        row.value = body.skin
    else:
        db.add(AppSetting(key="ui_skin", value=body.skin))
    db.commit()
    return {"ok": True}


@router.get("/categories")
def categories(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """大类清单（含建议小类）+ 题库中已实际出现的小类，供前端下拉与补全。"""
    used = (db.query(Question.category, Question.subcategory)
            .filter(Question.status != "deleted").distinct().all())
    used_sub: dict[str, set[str]] = {}
    for cat, sub in used:
        if cat and sub:
            used_sub.setdefault(cat, set()).add(sub)
    sub_map = {c: sorted(set(SUBCATEGORY_SUGGESTIONS.get(c, [])) | used_sub.get(c, set()))
               for c in set(CATEGORIES) | set(used_sub)}
    return {"categories": CATEGORIES, "subcategories": sub_map}


@router.get("/stats")
def stats(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    def count(status: str) -> int:
        return db.query(Question).filter(Question.status == status).count()

    return {
        "documents": db.query(Document).count(),
        "pending_review": count("pending_review"),
        "approved": count("approved"),
        "rejected": count("rejected"),
    }
