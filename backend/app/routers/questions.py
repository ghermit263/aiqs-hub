import difflib
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import DocChunk, Question, ReviewLog, User
from pydantic import BaseModel

from ..schemas import BatchReviewIn, ChunkOut, QuestionOut, QuestionUpdateIn, RejectIn
from ..security import get_current_user, require_reviewer

router = APIRouter(prefix="/questions", tags=["questions"])


def _log(db: Session, qid: int, action: str, user: User, detail: dict | None = None):
    db.add(ReviewLog(question_id=qid, action=action, operator_id=user.id, detail=detail))


def _get_or_404(db: Session, qid: int) -> Question:
    q = db.get(Question, qid)
    if not q or q.status == "deleted":
        raise HTTPException(404, "题目不存在")
    return q


@router.get("", response_model=dict)
def list_questions(
    status: str | None = None,
    q_type: str | None = None,
    document_id: int | None = None,
    category: str | None = None,
    keyword: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(Question).filter(Question.status != "deleted")
    if status:
        query = query.filter(Question.status == status)
    if q_type:
        query = query.filter(Question.q_type == q_type)
    if document_id:
        query = query.filter(Question.document_id == document_id)
    if category:
        query = query.filter(Question.category == category)
    if keyword:
        query = query.filter(or_(Question.stem.contains(keyword), Question.answer.contains(keyword)))
    total = query.count()
    items = (query.order_by(Question.id.desc())
             .offset((page - 1) * page_size).limit(page_size).all())
    return {
        "total": total,
        "items": [QuestionOut.model_validate(i).model_dump() for i in items],
    }


@router.get("/{qid}", response_model=dict)
def get_question(qid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = _get_or_404(db, qid)
    chunk = db.get(DocChunk, q.chunk_id) if q.chunk_id else None
    return {
        "question": QuestionOut.model_validate(q).model_dump(),
        "source": ChunkOut.model_validate(chunk).model_dump() if chunk else None,
    }


@router.put("/{qid}", response_model=QuestionOut)
def update_question(qid: int, body: QuestionUpdateIn,
                    db: Session = Depends(get_db), user: User = Depends(require_reviewer)):
    q = _get_or_404(db, qid)
    before = {"stem": q.stem, "options": q.options, "answer": q.answer,
              "analysis": q.analysis, "q_type": q.q_type}
    data = body.model_dump(exclude_none=True)
    if "options" in data:
        data["options"] = [o if isinstance(o, dict) else o for o in data["options"]]
    for k, v in data.items():
        setattr(q, k, v)
    _log(db, q.id, "edit", user, {"before": before})
    db.commit()
    db.refresh(q)
    return q


@router.post("/{qid}/approve", response_model=QuestionOut)
def approve(qid: int, db: Session = Depends(get_db), user: User = Depends(require_reviewer)):
    q = _get_or_404(db, qid)
    q.status = "approved"
    q.reviewed_by = user.id
    q.reviewed_at = datetime.now()
    q.reject_reason = None
    _log(db, q.id, "approve", user)
    db.commit()
    db.refresh(q)
    return q


@router.post("/{qid}/reject", response_model=QuestionOut)
def reject(qid: int, body: RejectIn, db: Session = Depends(get_db), user: User = Depends(require_reviewer)):
    q = _get_or_404(db, qid)
    q.status = "rejected"
    q.reject_reason = body.reason
    q.reviewed_by = user.id
    q.reviewed_at = datetime.now()
    _log(db, q.id, "reject", user, {"reason": body.reason})
    db.commit()
    db.refresh(q)
    return q


@router.delete("/{qid}")
def delete_question(qid: int, db: Session = Depends(get_db), user: User = Depends(require_reviewer)):
    q = _get_or_404(db, qid)
    q.status = "deleted"
    _log(db, q.id, "delete", user)
    db.commit()
    return {"ok": True}


@router.post("/batch-review")
def batch_review(body: BatchReviewIn, db: Session = Depends(get_db), user: User = Depends(require_reviewer)):
    if body.action not in ("approve", "reject"):
        raise HTTPException(400, "action 只能是 approve 或 reject")
    n = 0
    for qid in body.ids:
        q = db.get(Question, qid)
        if not q or q.status == "deleted":
            continue
        if body.action == "approve":
            q.status = "approved"
            q.reject_reason = None
        else:
            q.status = "rejected"
            q.reject_reason = body.reason
        q.reviewed_by = user.id
        q.reviewed_at = datetime.now()
        _log(db, q.id, body.action, user)
        n += 1
    db.commit()
    return {"ok": True, "count": n}


class BatchCategoryIn(BaseModel):
    ids: list[int]
    category: str = ""
    subcategory: str = ""


@router.post("/batch-category")
def batch_category(body: BatchCategoryIn, db: Session = Depends(get_db),
                   user: User = Depends(require_reviewer)):
    """批量修正分类（大类/小类），用于标准题库里成批归类。"""
    n = 0
    for qid in body.ids:
        q = db.get(Question, qid)
        if not q or q.status == "deleted":
            continue
        q.category = body.category
        q.subcategory = body.subcategory
        _log(db, q.id, "edit", user, {"category": body.category, "subcategory": body.subcategory})
        n += 1
    db.commit()
    return {"ok": True, "count": n}


@router.get("/{qid}/logs")
def question_logs(qid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    logs = (db.query(ReviewLog).filter(ReviewLog.question_id == qid)
            .order_by(ReviewLog.id.desc()).all())
    return [{"action": l.action, "detail": l.detail, "operator_id": l.operator_id,
             "created_at": l.created_at} for l in logs]


@router.get("/{qid}/duplicates")
def duplicates(qid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """同题型下题干相似度 > 0.6 的题目（MVP 用 difflib，量大后换 pg_trgm）。"""
    q = _get_or_404(db, qid)
    candidates = (db.query(Question)
                  .filter(Question.q_type == q.q_type, Question.id != q.id,
                          Question.status.in_(["pending_review", "approved"]))
                  .order_by(Question.id.desc()).limit(500).all())
    result = []
    for c in candidates:
        ratio = difflib.SequenceMatcher(None, q.stem, c.stem).ratio()
        if ratio > 0.6:
            result.append({"id": c.id, "stem": c.stem, "status": c.status,
                           "similarity": round(ratio, 2)})
    result.sort(key=lambda x: -x["similarity"])
    return result[:10]
