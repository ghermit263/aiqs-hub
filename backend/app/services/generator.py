"""生成任务编排：把任务的题量分摊到资料切片上，逐片调用 gateway 并落库为待审核题目。"""
import math
from datetime import datetime

from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..llm.gateway import build_provider, call_llm, extract_json
from ..logger import logger
from ..llm.prompts import SYSTEM_PROMPT, TYPE_LABELS, build_user_prompt
from ..models import DocChunk, GenerationTask, Question

VALID_TYPES = set(TYPE_LABELS)


def _distribute(type_counts: dict[str, int], n_chunks: int) -> list[dict[str, int]]:
    """把各题型总量分摊到各切片，轮转分配避免题目都挤在前几片。"""
    per_chunk: list[dict[str, int]] = [dict() for _ in range(n_chunks)]
    for qt, total in type_counts.items():
        if qt not in VALID_TYPES or total <= 0:
            continue
        for i in range(total):
            idx = i % n_chunks
            per_chunk[idx][qt] = per_chunk[idx].get(qt, 0) + 1
    return per_chunk


def _validate_question(q: dict) -> str | None:
    """返回 None 表示合格，否则返回丢弃原因。"""
    qt = q.get("q_type")
    if qt not in VALID_TYPES:
        return f"未知题型 {qt}"
    stem = (q.get("stem") or "").strip()
    if len(stem) < 5:
        return "题干过短"
    answer = str(q.get("answer") or "").strip()
    if not answer:
        return "缺少答案"
    options = q.get("options")
    if qt in ("single", "multiple"):
        if not options or len(options) < 2:
            return "选择题缺少选项"
        keys = {o.get("key") for o in options}
        if not set(answer) <= keys:
            return f"答案 {answer} 不在选项 {keys} 中"
        if qt == "single" and len(answer) != 1:
            return "单选题答案应为单个字母"
        if qt == "multiple" and len(answer) < 2:
            return "多选题答案应至少两个字母"
    if qt == "judge":
        if answer not in ("A", "B"):
            return "判断题答案应为 A 或 B"
        q["options"] = [{"key": "A", "text": "正确"}, {"key": "B", "text": "错误"}]
    if qt == "fill_blank":
        if not options:
            return "填空题缺少答案选项"
        if "_____" not in stem:
            return "填空题题干缺少空位标记"
    return None


def run_generation_task(task_id: int) -> None:
    """后台任务入口：独立 session。"""
    db: Session = SessionLocal()
    try:
        task = db.get(GenerationTask, task_id)
        if not task:
            return
        task.status = "running"
        try:
            provider = build_provider(db)
            task.model_name = f"{provider.name}:{provider.model}" if provider.model else provider.name
        except Exception:
            task.model_name = ""
        db.commit()

        chunks = (
            db.query(DocChunk)
            .filter(DocChunk.document_id == task.document_id)
            .order_by(DocChunk.chunk_index)
            .all()
        )
        if not chunks:
            raise ValueError("该资料没有可用切片，请先确认解析成功")

        type_counts: dict[str, int] = task.config.get("type_counts", {})
        total_requested = sum(v for k, v in type_counts.items() if k in VALID_TYPES)
        if total_requested <= 0:
            raise ValueError("任务未指定任何题型数量")

        # 切片数多于题量时，挑信息量大的切片（按字数排序取前 N）
        n_use = min(len(chunks), max(1, math.ceil(total_requested / 2)))
        use_chunks = sorted(chunks, key=lambda c: c.char_count, reverse=True)[:n_use]
        use_chunks.sort(key=lambda c: c.chunk_index)

        plan = _distribute(type_counts, len(use_chunks))
        difficulty = task.config.get("difficulty", "medium")
        category = task.config.get("category", "")
        subcategory = task.config.get("subcategory", "")
        saved = 0
        errors: list[str] = []

        for chunk, counts in zip(use_chunks, plan):
            if not counts:
                continue
            prompt = build_user_prompt(chunk.content, chunk.source_locator, counts, difficulty)
            try:
                raw = call_llm(db, SYSTEM_PROMPT, prompt, task_id=task.id)
                data = extract_json(raw)
            except Exception as e:  # noqa: BLE001
                errors.append(f"切片[{chunk.source_locator}]: {e}")
                continue
            for q in data.get("questions", []):
                reason = _validate_question(q)
                if reason:
                    errors.append(f"切片[{chunk.source_locator}]丢弃一题: {reason}")
                    continue
                db.add(Question(
                    task_id=task.id,
                    document_id=task.document_id,
                    chunk_id=chunk.id,
                    q_type=q["q_type"],
                    stem=q["stem"].strip(),
                    options=q.get("options"),
                    answer=str(q["answer"]).strip(),
                    analysis=(q.get("analysis") or "").strip(),
                    difficulty=q.get("difficulty", difficulty),
                    category=category,
                    subcategory=subcategory,
                    status="pending_review",
                ))
                saved += 1
            db.commit()

        task.question_count = saved
        task.finished_at = datetime.now()
        if saved == 0:
            task.status = "failed"
            task.error_msg = "未生成任何合格题目。" + ("；".join(errors[:5]) if errors else "")
            logger.error("生成任务失败 task=%s doc=%s: %s", task.id, task.document_id, task.error_msg[:500])
        else:
            task.status = "done"
            if errors:
                task.error_msg = f"部分内容未成功（共{len(errors)}条）: " + "；".join(errors[:5])
            logger.info("生成任务完成 task=%s doc=%s 入库=%s题 丢弃=%s条", task.id, task.document_id, saved, len(errors))
        db.commit()
    except Exception as e:  # noqa: BLE001
        db.rollback()
        logger.exception("生成任务异常 task=%s: %s", task_id, e)
        task = db.get(GenerationTask, task_id)
        if task:
            task.status = "failed"
            task.error_msg = str(e)[:2000]
            task.finished_at = datetime.now()
            db.commit()
    finally:
        db.close()
