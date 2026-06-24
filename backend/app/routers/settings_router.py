import json
import time

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..llm.gateway import PROVIDERS, build_provider, get_custom_guidance, get_effective_config, load_profiles
from ..logger import LOG_FILE, logger
from ..models import AppSetting, Document, LlmCallLog, Question, User
from ..schemas import CATEGORIES, SUBCATEGORY_SUGGESTIONS
from ..security import get_current_user, require_admin

router = APIRouter(tags=["settings"])


def _set(db: Session, key: str, value: str):
    row = db.get(AppSetting, key)
    if row:
        row.value = value
    else:
        db.add(AppSetting(key=key, value=value))


class ModelProfileIn(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    provider: str
    base_url: str = ""
    api_key: str = ""
    model: str = ""


class ModelsSaveIn(BaseModel):
    profiles: list[ModelProfileIn]
    active: str
    intranet_only: bool = False


@router.get("/settings/models")
def get_model_settings(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """返回全部模型配置（密钥脱敏）+ 当前启用项 + 可选供应商。"""
    profiles, active = load_profiles(db)
    cfg = get_effective_config(db)
    safe = [{
        "name": p["name"], "provider": p.get("provider", ""),
        "base_url": p.get("base_url", ""), "model": p.get("model", ""),
        "has_key": bool(p.get("api_key")),
        "api_key": (p["api_key"][:6] + "****") if p.get("api_key") else "",
    } for p in profiles]
    return {"profiles": safe, "active": active,
            "intranet_only": cfg["intranet_only"], "providers": list(PROVIDERS)}


@router.put("/settings/models")
def update_model_settings(body: ModelsSaveIn, db: Session = Depends(get_db),
                          user: User = Depends(require_admin)):
    """保存模型配置列表 + 启用项。空名校验、密钥保留（掩码/留空表示沿用旧值）。"""
    if not body.profiles:
        raise HTTPException(400, "至少保留一个模型配置")
    names = [p.name.strip() for p in body.profiles]
    if len(set(names)) != len(names):
        raise HTTPException(400, "模型配置名称不能重复")
    for p in body.profiles:
        if p.provider not in PROVIDERS:
            raise HTTPException(400, f"未知供应商: {p.provider}")
    # 旧配置里按名字取已存密钥，便于"留空=不改密钥"
    old_profiles, _ = load_profiles(db)
    old_keys = {p["name"]: p.get("api_key", "") for p in old_profiles}
    merged = []
    for p in body.profiles:
        key = p.api_key
        if not key or key.endswith("****"):
            key = old_keys.get(p.name, "")
        merged.append({"name": p.name.strip(), "provider": p.provider,
                       "base_url": p.base_url.strip(), "api_key": key, "model": p.model.strip()})
    active = body.active if any(m["name"] == body.active for m in merged) else merged[0]["name"]
    _set(db, "llm_profiles", json.dumps(merged, ensure_ascii=False))
    _set(db, "llm_active", active)
    _set(db, "intranet_only", "true" if body.intranet_only else "false")
    db.commit()
    return {"ok": True, "active": active}


class ActiveIn(BaseModel):
    active: str


@router.put("/settings/models/active")
def set_active_model(body: ActiveIn, db: Session = Depends(get_db),
                     user: User = Depends(require_admin)):
    """仅切换当前启用模型（下拉菜单切换用，无需整表保存）。"""
    profiles, _ = load_profiles(db)
    if not any(p["name"] == body.active for p in profiles):
        raise HTTPException(404, "该模型配置不存在")
    _set(db, "llm_active", body.active)
    db.commit()
    logger.info("切换启用模型 -> %s", body.active)
    return {"ok": True, "active": body.active}


@router.post("/settings/models/test")
def test_model(db: Session = Depends(get_db), user: User = Depends(require_admin)):
    """用当前启用配置发一次最小调用，验证连通性（先保存再测试）。"""
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


class GuidanceIn(BaseModel):
    guidance: str = ""


@router.get("/settings/guidance")
def get_guidance(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """本单位自定义命题指引（非通用规则）。"""
    return {"guidance": get_custom_guidance(db)}


@router.put("/settings/guidance")
def set_guidance(body: GuidanceIn, db: Session = Depends(get_db), user: User = Depends(require_admin)):
    _set(db, "custom_guidance", body.guidance.strip())
    db.commit()
    logger.info("更新自定义命题指引（%d 字）", len(body.guidance.strip()))
    return {"ok": True}


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
