import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..config import UPLOAD_DIR, settings
from ..database import SessionLocal, get_db
from ..logger import logger
from ..models import DocChunk, Document, Question, User
from ..schemas import ChunkOut, DocumentOut
from ..security import get_current_user
from ..services.chunker import chunk_segments
from ..services.parsers import SUPPORTED_EXTS, parse_file

router = APIRouter(prefix="/documents", tags=["documents"])


def _parse_document(doc_id: int) -> None:
    db = SessionLocal()
    try:
        doc = db.get(Document, doc_id)
        if not doc:
            return
        doc.parse_status = "parsing"
        db.commit()
        try:
            segments = parse_file(doc.file_path, doc.file_type)
            chunks = chunk_segments(segments)
            if not chunks:
                raise ValueError("未能从文件中提取到任何文本")
            for i, (locator, text) in enumerate(chunks):
                db.add(DocChunk(document_id=doc.id, chunk_index=i,
                                content=text, source_locator=locator, char_count=len(text)))
            doc.chunk_count = len(chunks)
            doc.parse_status = "done"
            doc.parse_error = None
        except Exception as e:  # noqa: BLE001
            doc.parse_status = "failed"
            doc.parse_error = str(e)[:2000]
            logger.error("解析失败 doc=%s file=%s: %s", doc.id, doc.filename, str(e)[:500])
        else:
            logger.info("解析完成 doc=%s file=%s 切片=%s", doc.id, doc.filename, doc.chunk_count)
        db.commit()
    finally:
        db.close()


@router.post("", response_model=DocumentOut)
async def upload(file: UploadFile, background: BackgroundTasks,
                 db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ext = Path(file.filename or "").suffix.lower().lstrip(".")
    if ext not in SUPPORTED_EXTS:
        raise HTTPException(400, f"不支持的文件类型 .{ext}，支持: {sorted(SUPPORTED_EXTS)}")
    content = await file.read()
    if len(content) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(400, f"文件超过 {settings.max_upload_mb}MB 限制")
    save_path = UPLOAD_DIR / f"{uuid.uuid4().hex}.{ext}"
    save_path.write_bytes(content)
    doc = Document(filename=file.filename or save_path.name, file_type=ext,
                   file_path=str(save_path), file_size=len(content), uploaded_by=user.id)
    db.add(doc)
    db.commit()
    db.refresh(doc)
    background.add_task(_parse_document, doc.id)
    return doc


@router.get("", response_model=list[DocumentOut])
def list_documents(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(Document).order_by(Document.id.desc()).all()


@router.get("/{doc_id}", response_model=DocumentOut)
def get_document(doc_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    doc = db.get(Document, doc_id)
    if not doc:
        raise HTTPException(404, "资料不存在")
    return doc


@router.get("/{doc_id}/chunks", response_model=list[ChunkOut])
def list_chunks(doc_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return (db.query(DocChunk).filter(DocChunk.document_id == doc_id)
            .order_by(DocChunk.chunk_index).all())


@router.delete("/{doc_id}")
def delete_document(doc_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    doc = db.get(Document, doc_id)
    if not doc:
        raise HTTPException(404, "资料不存在")
    if user.role == "uploader" and doc.uploaded_by != user.id:
        raise HTTPException(403, "上传人只能删除自己上传的资料")
    n_questions = db.query(Question).filter(
        Question.document_id == doc_id, Question.status != "deleted").count()
    if n_questions:
        raise HTTPException(400, f"该资料已有 {n_questions} 道关联题目，不能删除（题目仍需溯源）")
    try:
        Path(doc.file_path).unlink(missing_ok=True)
    except OSError:
        pass
    db.delete(doc)
    db.commit()
    return {"ok": True}
