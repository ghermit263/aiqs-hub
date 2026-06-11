from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Document, GenerationTask, User
from ..schemas import Q_TYPES, TaskCreateIn, TaskOut
from ..security import get_current_user, require_reviewer
from ..services.generator import run_generation_task

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("", response_model=TaskOut)
def create_task(body: TaskCreateIn, background: BackgroundTasks,
                db: Session = Depends(get_db), user: User = Depends(require_reviewer)):
    doc = db.get(Document, body.document_id)
    if not doc:
        raise HTTPException(404, "资料不存在")
    if doc.parse_status != "done":
        raise HTTPException(400, f"资料尚未解析完成（当前状态: {doc.parse_status}）")
    counts = {k: v for k, v in body.type_counts.items() if k in Q_TYPES and v > 0}
    if not counts:
        raise HTTPException(400, "请至少指定一种题型的数量")
    if sum(counts.values()) > 200:
        raise HTTPException(400, "单次任务题量请不要超过 200 道")
    task = GenerationTask(document_id=doc.id,
                          config={"type_counts": counts, "difficulty": body.difficulty,
                                  "category": body.category, "subcategory": body.subcategory},
                          created_by=user.id)
    db.add(task)
    db.commit()
    db.refresh(task)
    background.add_task(run_generation_task, task.id)
    return task


@router.get("", response_model=list[TaskOut])
def list_tasks(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(GenerationTask).order_by(GenerationTask.id.desc()).limit(100).all()


@router.get("/{task_id}", response_model=TaskOut)
def get_task(task_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    task = db.get(GenerationTask, task_id)
    if not task:
        raise HTTPException(404, "任务不存在")
    return task
