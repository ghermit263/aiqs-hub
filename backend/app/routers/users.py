"""用户管理（仅管理员）：审批注册、调整角色、停用、重置密码、手工建号。"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from ..security import hash_password, require_admin

router = APIRouter(prefix="/users", tags=["users"])

VALID_ROLES = ("uploader", "reviewer", "admin")
VALID_STATUS = ("pending", "active", "disabled")


class UserUpdateIn(BaseModel):
    role: str | None = None
    status: str | None = None
    display_name: str | None = None
    new_password: str | None = Field(default=None, min_length=6, max_length=64)


class UserCreateIn(BaseModel):
    username: str = Field(min_length=2, max_length=32)
    password: str = Field(min_length=6, max_length=64)
    display_name: str = ""
    role: str = "uploader"


def _user_out(u: User) -> dict:
    return {"id": u.id, "username": u.username, "display_name": u.display_name,
            "role": u.role, "status": u.status, "created_at": u.created_at}


@router.get("")
def list_users(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return [_user_out(u) for u in db.query(User).order_by(User.id).all()]


@router.post("")
def create_user(body: UserCreateIn, db: Session = Depends(get_db),
                admin: User = Depends(require_admin)):
    if body.role not in VALID_ROLES:
        raise HTTPException(400, f"角色须为 {VALID_ROLES}")
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(400, "用户名已存在")
    u = User(username=body.username, password_hash=hash_password(body.password),
             display_name=body.display_name or body.username, role=body.role, status="active")
    db.add(u)
    db.commit()
    return _user_out(u)


@router.put("/{user_id}")
def update_user(user_id: int, body: UserUpdateIn, db: Session = Depends(get_db),
                admin: User = Depends(require_admin)):
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(404, "用户不存在")
    if body.role is not None:
        if body.role not in VALID_ROLES:
            raise HTTPException(400, f"角色须为 {VALID_ROLES}")
        if u.id == admin.id and body.role != "admin":
            raise HTTPException(400, "不能取消自己的管理员角色")
        u.role = body.role
    if body.status is not None:
        if body.status not in VALID_STATUS:
            raise HTTPException(400, f"状态须为 {VALID_STATUS}")
        if u.id == admin.id and body.status != "active":
            raise HTTPException(400, "不能停用自己的账号")
        u.status = body.status
    if body.display_name is not None:
        u.display_name = body.display_name
    if body.new_password:
        u.password_hash = hash_password(body.new_password)
    db.commit()
    return _user_out(u)
