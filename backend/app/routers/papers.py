from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..logger import logger
from ..models import Paper, Question, User
from ..security import require_reviewer
from ..services.paper import (
    DIFF_LABELS, TYPE_LABELS, build_picked_from_ids, find_alternatives,
    render_picked, select_questions,
)

router = APIRouter(prefix="/papers", tags=["papers"])


class CriterionIn(BaseModel):
    q_type: str
    category: str = "any"     # any 或 具体大类
    difficulty: str = "any"   # any/easy/medium/hard
    count: int = Field(ge=1, le=100)
    score: int = Field(default=1, ge=1, le=100)


class DraftIn(BaseModel):
    criteria: list[CriterionIn] = Field(min_length=1)


class SectionIn(BaseModel):
    q_type: str
    score: int = Field(default=1, ge=1, le=100)
    question_ids: list[int]


class PaperCreateIn(BaseModel):
    title: str = Field(min_length=2, max_length=100)
    venue: str = Field(default="", max_length=50)
    sections: list[SectionIn] = Field(min_length=1)
    versions: list[str] = Field(default_factory=lambda: ["A", "B"])  # 选 ["A"] 即只出A卷


def _q_brief(q: Question) -> dict:
    return {"id": q.id, "q_type": q.q_type, "stem": q.stem, "options": q.options,
            "answer": q.answer, "difficulty": q.difficulty,
            "category": q.category, "subcategory": q.subcategory}


@router.get("/stock")
def stock(db: Session = Depends(get_db), user: User = Depends(require_reviewer)):
    """各题型×大类的可用题量，组卷页提示用。"""
    rows = (db.query(Question.q_type, Question.category)
            .filter(Question.status == "approved").all())
    result: dict[str, dict[str, int]] = {}
    for q_type, category in rows:
        d = result.setdefault(q_type, {})
        d["any"] = d.get("any", 0) + 1
        cat = category or "未分类"
        d[cat] = d.get(cat, 0) + 1
    return result


@router.post("/draft")
def draft(body: DraftIn, db: Session = Depends(get_db), user: User = Depends(require_reviewer)):
    """按条件自动抽题，返回可微调的草稿（题目按题型分组，含大类，供前端换题/调整）。"""
    for c in body.criteria:
        if c.q_type not in TYPE_LABELS:
            raise HTTPException(400, f"未知题型: {c.q_type}")
    try:
        picked = select_questions(db, [c.model_dump() for c in body.criteria])
    except ValueError as e:
        raise HTTPException(400, str(e))
    # 同一题型可能来自多行不同分值的条件：按题型聚合，分值取该题所在条件
    sections = []
    cat_summary: dict[str, int] = {}
    for q_type, items in picked.items():
        qs = []
        for q, score in items:
            brief = _q_brief(q)
            brief["score"] = score
            qs.append(brief)
            cat_summary[q.category or "未分类"] = cat_summary.get(q.category or "未分类", 0) + 1
        sections.append({"q_type": q_type, "label": TYPE_LABELS[q_type], "questions": qs})
    sections.sort(key=lambda s: list(TYPE_LABELS).index(s["q_type"]))
    return {"sections": sections, "category_summary": cat_summary,
            "total_questions": sum(len(s["questions"]) for s in sections),
            "total_score": sum(q["score"] for s in sections for q in s["questions"])}


@router.get("/alternatives")
def alternatives(q_type: str, category: str = "any", difficulty: str = "any",
                 exclude: str = "", db: Session = Depends(get_db),
                 user: User = Depends(require_reviewer)):
    """换题候选：同题型（可选同大类/难度），排除已用题目。"""
    exclude_ids = [int(x) for x in exclude.split(",") if x.strip().isdigit()]
    cands = find_alternatives(db, q_type, category, difficulty, exclude_ids)
    return [_q_brief(q) for q in cands]


VALID_VERSIONS = ("A", "B", "C", "D")


@router.post("/preview")
def preview(body: PaperCreateIn, db: Session = Depends(get_db),
            user: User = Depends(require_reviewer)):
    """组卷前预览：按微调后的题目即时生成各卷别排版（含题号/乱序/答案），不落库不生成文件。"""
    versions = tuple(v for v in body.versions if v in VALID_VERSIONS) or ("A",)
    try:
        from ..services.paper import build_versions
        picked = build_picked_from_ids(db, [s.model_dump() for s in body.sections])
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"versions": list(versions), "preview": build_versions(picked, versions)}


@router.post("")
def create_paper(body: PaperCreateIn, db: Session = Depends(get_db),
                 user: User = Depends(require_reviewer)):
    """定稿出卷：用微调后的显式题目ID生成试卷 zip + 独立 docx，可选卷别。"""
    versions = tuple(v for v in body.versions if v in VALID_VERSIONS) or ("A",)
    try:
        picked = build_picked_from_ids(db, [s.model_dump() for s in body.sections])
        result = render_picked(body.title, body.venue, picked, versions)
    except ValueError as e:
        raise HTTPException(400, str(e))
    cat_dist: dict[str, int] = {}
    for items in picked.values():
        for q, _ in items:
            cat_dist[q.category or "未分类"] = cat_dist.get(q.category or "未分类", 0) + 1
    paper = Paper(title=body.title, venue=body.venue,
                  config={"sections": [s.model_dump() for s in body.sections],
                          "category_distribution": cat_dist,
                          "versions": result["versions"], "files": result["files"],
                          "work_dir": result["work_dir"], "preview": result["preview"]},
                  question_count=result["question_count"], total_score=result["total_score"],
                  file_path=result["file_path"], created_by=user.id)
    db.add(paper)
    db.commit()
    db.refresh(paper)
    logger.info("组卷完成 paper=%s 标题=%s 卷别=%s 题数=%s 满分=%s 大类=%s",
                paper.id, paper.title, result["versions"], paper.question_count,
                paper.total_score, cat_dist)
    return {"id": paper.id, "question_count": paper.question_count,
            "total_score": paper.total_score, "category_distribution": cat_dist,
            "versions": result["versions"], "preview": result["preview"],
            "files": result["files"],
            "download_url": f"/api/v1/papers/{paper.id}/download"}


@router.get("")
def list_papers(db: Session = Depends(get_db), user: User = Depends(require_reviewer)):
    papers = db.query(Paper).order_by(Paper.id.desc()).limit(50).all()
    out = []
    for p in papers:
        cfg = p.config or {}
        out.append({
            "id": p.id, "title": p.title, "venue": p.venue,
            "question_count": p.question_count, "total_score": p.total_score,
            "category_distribution": cfg.get("category_distribution", {}),
            "versions": cfg.get("versions", ["A", "B"]),
            "files": cfg.get("files", []),
            "created_at": p.created_at,
            "download_url": f"/api/v1/papers/{p.id}/download"})
    return out


@router.get("/{paper_id}")
def get_paper(paper_id: int, db: Session = Depends(get_db), user: User = Depends(require_reviewer)):
    """单份试卷详情，含可重新预览的排版数据与独立 docx 列表。"""
    p = db.get(Paper, paper_id)
    if not p:
        raise HTTPException(404, "试卷不存在")
    cfg = p.config or {}
    return {"id": p.id, "title": p.title, "venue": p.venue,
            "question_count": p.question_count, "total_score": p.total_score,
            "versions": cfg.get("versions", []), "preview": cfg.get("preview", {}),
            "files": cfg.get("files", []),
            "download_url": f"/api/v1/papers/{p.id}/download"}


@router.get("/{paper_id}/download")
def download(paper_id: int, db: Session = Depends(get_db)):
    p = db.get(Paper, paper_id)
    if not p or not Path(p.file_path).exists():
        raise HTTPException(404, "试卷文件不存在")
    return FileResponse(p.file_path, filename=Path(p.file_path).name,
                        media_type="application/zip")


@router.get("/{paper_id}/file")
def download_file(paper_id: int, name: str, db: Session = Depends(get_db)):
    """下载某份试卷里的单个 docx（方便单独微调），name 须在该卷的 files 列表中。"""
    p = db.get(Paper, paper_id)
    if not p:
        raise HTTPException(404, "试卷不存在")
    cfg = p.config or {}
    if name not in cfg.get("files", []):
        raise HTTPException(404, "文件不存在")
    work_dir = cfg.get("work_dir", "")
    fpath = Path(work_dir) / name
    if not fpath.exists():
        raise HTTPException(404, "文件已被清理，请重新组卷")
    return FileResponse(str(fpath), filename=name,
                        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
