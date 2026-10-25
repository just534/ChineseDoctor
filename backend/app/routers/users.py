from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import client_ip, require_perm
from ..models import Role, User, user_roles
from ..schemas import Msg, Page, ResetPasswordIn, UserCreate, UserOut, UserUpdate
from ..security import hash_password, validate_password_strength
from ..services import audit

router = APIRouter(prefix="/users", tags=["用户管理"])


def _can_manage(actor: User, target: User) -> bool:
    """防越权：只能管理权限不超过自己的用户；超级管理员只能由超级管理员管理。"""
    if actor.is_superuser:
        return True
    if target.is_superuser:
        return False
    return target.permission_codes <= actor.permission_codes


def _load_roles(db: Session, actor: User, role_ids: list[int]) -> list[Role]:
    roles = list(db.scalars(select(Role).where(Role.id.in_(role_ids)))) if role_ids else []
    if len(roles) != len(set(role_ids)):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "角色不存在")
    if not actor.is_superuser:
        for r in roles:
            if r.code == "super_admin" or not {p.code for p in r.permissions} <= actor.permission_codes:
                raise HTTPException(status.HTTP_403_FORBIDDEN, f"无权分配角色「{r.name}」")
    return roles


@router.get("", response_model=Page[UserOut])
def list_users(
    keyword: str = "",
    role_id: int | None = None,
    is_active: bool | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    _: User = Depends(require_perm("user:read")),
    db: Session = Depends(get_db),
):
    q = select(User)
    if keyword:
        kw = f"%{keyword.strip()}%"
        q = q.where(or_(User.username.ilike(kw), User.nickname.ilike(kw), User.email.ilike(kw), User.phone.ilike(kw)))
    if role_id:
        q = q.where(User.id.in_(select(user_roles.c.user_id).where(user_roles.c.role_id == role_id)))
    if is_active is not None:
        q = q.where(User.is_active.is_(is_active))
    total = db.scalar(select(func.count()).select_from(q.subquery()))
    items = db.scalars(q.order_by(User.id.desc()).offset((page - 1) * size).limit(size)).all()
    return Page(items=items, total=total, page=page, size=size)


@router.post("", response_model=UserOut, status_code=201)
def create_user(
    body: UserCreate,
    request: Request,
    actor: User = Depends(require_perm("user:create")),
    db: Session = Depends(get_db),
):
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
        phone=body.phone,
        is_active=body.is_active,
        remark=body.remark,
        must_change_password=body.must_change_password,
        password_hash=hash_password(body.password),
    )
    user.roles = _load_roles(db, actor, body.role_ids)
    user.is_superuser = any(r.code == "super_admin" for r in user.roles)
    db.add(user)
    db.flush()
    audit.record(db, "user.create", user=actor, target=user.username, ip=client_ip(request),
                 detail=f"角色：{','.join(r.name for r in user.roles)}")
    return user


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: int, _: User = Depends(require_perm("user:read")), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "用户不存在")
    return user


@router.put("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    body: UserUpdate,
    request: Request,
    actor: User = Depends(require_perm("user:update")),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "用户不存在")
    if not _can_manage(actor, user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "无权修改该用户")
    data = body.model_dump(exclude_unset=True)
    changes = []
    if "role_ids" in data:
        role_ids = data.pop("role_ids") or []
        roles = _load_roles(db, actor, role_ids)
        becomes_super = any(r.code == "super_admin" for r in roles)
        if user.id == actor.id and actor.is_superuser and not becomes_super:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "不能移除自己的超级管理员角色")
        user.roles = roles
        user.is_superuser = becomes_super
        user.token_version += 1
        changes.append(f"角色→{','.join(r.name for r in roles) or '无'}")
    if data.get("is_active") is False:
        if user.id == actor.id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "不能禁用自己")
        if user.is_active:
            user.token_version += 1
    if "email" in data and data["email"]:
        email = data["email"].lower()
        if db.scalar(select(User.id).where(func.lower(User.email) == email, User.id != user.id)):
            raise HTTPException(status.HTTP_409_CONFLICT, "邮箱已被使用")
        data["email"] = email
    for k, v in data.items():
        if getattr(user, k) != v:
            changes.append(f"{k}→{v}")
        setattr(user, k, v)
    audit.record(db, "user.update", user=actor, target=user.username, detail="；".join(changes), ip=client_ip(request))
    return user


@router.delete("/{user_id}", response_model=Msg)
def delete_user(
    user_id: int,
    request: Request,
    actor: User = Depends(require_perm("user:delete")),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "用户不存在")
    if user.id == actor.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "不能删除自己")
    if not _can_manage(actor, user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "无权删除该用户")
    if user.is_superuser and db.scalar(select(func.count(User.id)).where(User.is_superuser.is_(True))) <= 1:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "至少保留一个超级管理员")
    name = user.username
    db.delete(user)
    audit.record(db, "user.delete", user=actor, target=name, ip=client_ip(request))
    return Msg(message="已删除")


@router.post("/{user_id}/reset-password", response_model=Msg)
def reset_password(
    user_id: int,
    body: ResetPasswordIn,
    request: Request,
    actor: User = Depends(require_perm("user:reset_password")),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "用户不存在")
    if not _can_manage(actor, user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "无权重置该用户密码")
    if err := validate_password_strength(body.new_password):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, err)
    user.password_hash = hash_password(body.new_password)
    user.must_change_password = user.id != actor.id
    user.token_version += 1
    user.failed_logins = 0
    user.locked_until = None
    audit.record(db, "user.reset_password", user=actor, target=user.username, ip=client_ip(request))
    return Msg(message="密码已重置，用户下次登录需修改密码")


@router.post("/{user_id}/unlock", response_model=Msg)
def unlock(
    user_id: int,
    request: Request,
    actor: User = Depends(require_perm("user:update")),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "用户不存在")
    user.failed_logins = 0
    user.locked_until = None
    audit.record(db, "user.unlock", user=actor, target=user.username, ip=client_ip(request))
    return Msg(message="已解锁")


@router.post("/{user_id}/kick", response_model=Msg)
def kick(
    user_id: int,
    request: Request,
    actor: User = Depends(require_perm("user:update")),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "用户不存在")
    if not _can_manage(actor, user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "无权操作该用户")
    user.token_version += 1
    audit.record(db, "user.kick", user=actor, target=user.username, ip=client_ip(request))
    return Msg(message="已强制下线")
