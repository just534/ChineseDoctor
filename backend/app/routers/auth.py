from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..deps import client_ip, get_current_user
from ..models import Role, User
from ..permissions import PERMISSION_CODES
from ..schemas import (
    ChangePasswordIn,
    LoginIn,
    MeOut,
    Msg,
    ProfileIn,
    RefreshIn,
    RegisterIn,
    TokenOut,
    UserOut,
)
from ..security import (
    DUMMY_HASH,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    validate_password_strength,
    verify_password,
)
from ..services import audit

router = APIRouter(prefix="/auth", tags=["认证"])
settings = get_settings()


def _tokens(user: User) -> TokenOut:
    return TokenOut(
        access_token=create_access_token(user.id, user.token_version),
        refresh_token=create_refresh_token(user.id, user.token_version),
        expires_in=settings.access_token_minutes * 60,
    )


def me_out(user: User) -> MeOut:
    perms = sorted(PERMISSION_CODES) if user.is_superuser else sorted(user.permission_codes)
    return MeOut(**UserOut.model_validate(user).model_dump(), permissions=perms)


@router.get("/config")
def public_config():
    return {
        "app_name": settings.app_name,
        "allow_registration": settings.allow_registration,
        "ai_enabled": settings.ai_enabled,
    }


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, request: Request, db: Session = Depends(get_db)):
    ip = client_ip(request)
    name = body.username.strip()
    user = db.scalar(
        select(User).where(or_(func.lower(User.username) == name.lower(), func.lower(User.email) == name.lower()))
    )
    now = datetime.now(timezone.utc)

    if user and user.locked_until and _aware(user.locked_until) > now:
        minutes = int((_aware(user.locked_until) - now).total_seconds() // 60) + 1
        audit.record(db, "login", user=user, ip=ip, success=False, detail="账号锁定中")
        raise HTTPException(status.HTTP_423_LOCKED, f"登录失败次数过多，请 {minutes} 分钟后再试")

    if not user:
        verify_password(body.password, DUMMY_HASH)
        audit.record(db, "login", username=name[:50], ip=ip, success=False, detail="用户不存在")
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "用户名或密码错误")

    if not verify_password(body.password, user.password_hash):
        user.failed_logins += 1
        detail = "密码错误"
        if user.failed_logins >= settings.max_failed_logins:
            user.locked_until = now + timedelta(minutes=settings.lockout_minutes)
            user.failed_logins = 0
            detail = "密码错误，账号已锁定"
        audit.record(db, "login", user=user, ip=ip, success=False, detail=detail)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "用户名或密码错误")

    if not user.is_active:
        audit.record(db, "login", user=user, ip=ip, success=False, detail="账号已禁用")
        raise HTTPException(status.HTTP_403_FORBIDDEN, "账号已被禁用，请联系管理员")

    user.failed_logins = 0
    user.locked_until = None
    user.last_login_at = now
    user.last_login_ip = ip
    audit.record(db, "login", user=user, ip=ip)
    return _tokens(user)


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


@router.post("/refresh", response_model=TokenOut)
def refresh(body: RefreshIn, db: Session = Depends(get_db)):
    payload = decode_token(body.refresh_token, "refresh")
    user = db.get(User, int(payload["sub"])) if payload else None
    if not user or not user.is_active or user.token_version != payload.get("ver"):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "登录已失效，请重新登录")
    return _tokens(user)


@router.post("/register", response_model=TokenOut, status_code=201)
def register(body: RegisterIn, request: Request, db: Session = Depends(get_db)):
    if not settings.allow_registration:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "当前未开放注册")
    if err := validate_password_strength(body.password):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, err)
    if db.scalar(select(User.id).where(func.lower(User.username) == body.username.lower())):
        raise HTTPException(status.HTTP_409_CONFLICT, "用户名已存在")
    if body.email and db.scalar(select(User.id).where(func.lower(User.email) == body.email.lower())):
        raise HTTPException(status.HTTP_409_CONFLICT, "邮箱已被使用")
    user = User(
        username=body.username,
        email=body.email.lower() if body.email else None,
        nickname=body.nickname or body.username,
        password_hash=hash_password(body.password),
        last_login_at=datetime.now(timezone.utc),
        last_login_ip=client_ip(request),
    )
    role = db.scalar(select(Role).where(Role.code == settings.default_role))
    if role:
        user.roles = [role]
    db.add(user)
    db.flush()
    audit.record(db, "register", user=user, ip=client_ip(request))
    return _tokens(user)


@router.get("/me", response_model=MeOut)
def me(user: User = Depends(get_current_user)):
    return me_out(user)


@router.put("/me", response_model=MeOut)
def update_profile(body: ProfileIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    data = body.model_dump(exclude_unset=True)
    if "email" in data and data["email"]:
        email = data["email"].lower()
        if db.scalar(select(User.id).where(func.lower(User.email) == email, User.id != user.id)):
            raise HTTPException(status.HTTP_409_CONFLICT, "邮箱已被使用")
        data["email"] = email
    for k, v in data.items():
        setattr(user, k, v)
    db.commit()
    return me_out(user)


@router.post("/change-password", response_model=TokenOut)
def change_password(
    body: ChangePasswordIn, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    if not verify_password(body.old_password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "原密码错误")
    if err := validate_password_strength(body.new_password):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, err)
    if body.old_password == body.new_password:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "新密码不能与原密码相同")
    user.password_hash = hash_password(body.new_password)
    user.must_change_password = False
    user.token_version += 1
    audit.record(db, "change_password", user=user, ip=client_ip(request))
    return _tokens(user)


@router.post("/logout-all", response_model=Msg)
def logout_all(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user.token_version += 1
    audit.record(db, "logout_all", user=user, ip=client_ip(request))
    return Msg(message="已退出所有设备")
