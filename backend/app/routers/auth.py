from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from ..schemas import LoginIn, TokenOut
from ..security import create_token, get_current_user, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterIn(BaseModel):
    username: str = Field(min_length=2, max_length=32)
    password: str = Field(min_length=6, max_length=64)
    display_name: str = Field(default="", max_length=32)


class ChangePasswordIn(BaseModel):
    old_password: str
    new_password: str = Field(min_length=6, max_length=64)


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == body.username).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "用户名或密码错误")
    if user.status == "pending":
        raise HTTPException(403, "账号正在等待管理员审批，请稍后再试")
    if user.status == "disabled":
        raise HTTPException(403, "账号已停用，请联系管理员")
    return TokenOut(token=create_token(user), username=user.username,
                    display_name=user.display_name, role=user.role)


@router.post("/register")
def register(body: RegisterIn, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(400, "用户名已存在")
    db.add(User(username=body.username, password_hash=hash_password(body.password),
                display_name=body.display_name or body.username,
                role="uploader", status="pending"))
    db.commit()
    return {"ok": True, "message": "注册成功，请等待管理员审批后登录"}


@router.post("/change-password")
def change_password(body: ChangePasswordIn, db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    if not verify_password(body.old_password, user.password_hash):
        raise HTTPException(400, "原密码错误")
    user.password_hash = hash_password(body.new_password)
    db.commit()
    return {"ok": True, "message": "密码已修改，下次登录请使用新密码"}


@router.get("/me", response_model=TokenOut)
def me(user: User = Depends(get_current_user)):
    return TokenOut(token="", username=user.username,
                    display_name=user.display_name, role=user.role)
