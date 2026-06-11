from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import ExportRecord, Question, User
from ..schemas import ExportIn
from ..security import require_reviewer
from ..services.exporter import export_questions

router = APIRouter(prefix="/exports", tags=["exports"])


@router.post("")
def create_export(body: ExportIn, db: Session = Depends(get_db), user: User = Depends(require_reviewer)):
    query = db.query(Question).filter(Question.status == "approved")
    if body.ids:
        query = query.filter(Question.id.in_(body.ids))
    else:
        if body.q_types:
            query = query.filter(Question.q_type.in_(body.q_types))
        if body.document_id:
            query = query.filter(Question.document_id == body.document_id)
        if body.keyword:
            query = query.filter(Question.stem.contains(body.keyword))
    questions = query.order_by(Question.q_type, Question.id).all()
    if not questions:
        raise HTTPException(400, "没有符合条件的已审核题目可导出")
    path = export_questions(questions)
    rec = ExportRecord(filter=body.model_dump(), question_count=len(questions),
                       file_path=path, exported_by=user.id)
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return {"id": rec.id, "question_count": len(questions),
            "filename": Path(path).name, "download_url": f"/api/v1/exports/{rec.id}/download"}


@router.get("")
def list_exports(db: Session = Depends(get_db), user: User = Depends(require_reviewer)):
    recs = db.query(ExportRecord).order_by(ExportRecord.id.desc()).limit(50).all()
    return [{"id": r.id, "question_count": r.question_count,
             "filename": Path(r.file_path).name, "created_at": r.created_at,
             "download_url": f"/api/v1/exports/{r.id}/download"} for r in recs]


@router.get("/{rec_id}/download")
def download(rec_id: int, db: Session = Depends(get_db)):
    rec = db.get(ExportRecord, rec_id)
    if not rec or not Path(rec.file_path).exists():
        raise HTTPException(404, "导出文件不存在")
    return FileResponse(rec.file_path, filename=Path(rec.file_path).name,
                        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
