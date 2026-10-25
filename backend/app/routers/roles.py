from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import client_ip, require_perm
from ..models import Permission, Role, User, user_roles
from ..schemas import Msg, PermissionOut, RoleIn, RoleOut, RoleUpdate
from ..services import audit

router = APIRouter(tags=["角色权限"])


def _role_out(db: Session, role: Role) -> RoleOut:
    count = db.scalar(select(func.count()).select_from(user_roles).where(user_roles.c.role_id == role.id))
    return RoleOut.model_validate(
        {
            **{k: getattr(role, k) for k in ("id", "code", "name", "description", "is_system", "is_active", "sort", "created_at")},
            "permissions": sorted(p.code for p in role.permissions),
            "user_count": count,
        }
    )


def _resolve_perms(db: Session, codes: list[str]) -> list[Permission]:
    perms = list(db.scalars(select(Permission).where(Permission.code.in_(codes)))) if codes else []
    unknown = set(codes) - {p.code for p in perms}
    if unknown:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"未知权限点：{', '.join(sorted(unknown))}")
    return perms


@router.get("/permissions", response_model=list[PermissionOut])
def list_permissions(_: User = Depends(require_perm("role:read")), db: Session = Depends(get_db)):
    return db.scalars(select(Permission).order_by(Permission.sort)).all()


@router.get("/roles", response_model=list[RoleOut])
def list_roles(_: User = Depends(require_perm("role:read")), db: Session = Depends(get_db)):
    roles = db.scalars(select(Role).order_by(Role.sort, Role.id)).all()
    return [_role_out(db, r) for r in roles]


@router.get("/roles/options", response_model=list[RoleOut])
def role_options(_: User = Depends(require_perm("user:read")), db: Session = Depends(get_db)):
    """供用户管理下拉选择使用"""
    roles = db.scalars(select(Role).where(Role.is_active.is_(True)).order_by(Role.sort, Role.id)).all()
    return [_role_out(db, r) for r in roles]


@router.post("/roles", response_model=RoleOut, status_code=201)
def create_role(
    body: RoleIn, request: Request, actor: User = Depends(require_perm("role:manage")), db: Session = Depends(get_db)
):
    if db.scalar(select(Role.id).where(Role.code == body.code)):
        raise HTTPException(status.HTTP_409_CONFLICT, "角色编码已存在")
    role = Role(code=body.code, name=body.name, description=body.description, is_active=body.is_active, sort=body.sort)
    role.permissions = _resolve_perms(db, body.permissions)
    db.add(role)
    db.flush()
    audit.record(db, "role.create", user=actor, target=role.name, detail=",".join(body.permissions), ip=client_ip(request))
    return _role_out(db, role)


@router.put("/roles/{role_id}", response_model=RoleOut)
def update_role(
    role_id: int,
    body: RoleUpdate,
    request: Request,
    actor: User = Depends(require_perm("role:manage")),
    db: Session = Depends(get_db),
):
    role = db.get(Role, role_id)
    if not role:
        raise HTTPException(404, "角色不存在")
    data = body.model_dump(exclude_unset=True)
    if role.code == "super_admin" and ("permissions" in data or data.get("is_active") is False):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "超级管理员角色的权限不可修改")
    if "permissions" in data:
        role.permissions = _resolve_perms(db, data.pop("permissions") or [])
    for k, v in data.items():
        setattr(role, k, v)
    audit.record(
        db, "role.update", user=actor, target=role.name,
        detail=",".join(sorted(p.code for p in role.permissions)), ip=client_ip(request),
    )
    return _role_out(db, role)


@router.delete("/roles/{role_id}", response_model=Msg)
def delete_role(
    role_id: int, request: Request, actor: User = Depends(require_perm("role:manage")), db: Session = Depends(get_db)
):
    role = db.get(Role, role_id)
    if not role:
        raise HTTPException(404, "角色不存在")
    if role.is_system:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "内置角色不可删除")
    count = db.scalar(select(func.count()).select_from(user_roles).where(user_roles.c.role_id == role.id))
    if count:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"仍有 {count} 个用户使用该角色，请先调整")
    name = role.name
    db.delete(role)
    audit.record(db, "role.delete", user=actor, target=name, ip=client_ip(request))
    return Msg(message="已删除")
