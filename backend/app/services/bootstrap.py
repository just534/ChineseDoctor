import logging
import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import Permission, Role, User
from ..permissions import BUILTIN_ROLES, PERMISSIONS
from ..security import hash_password

log = logging.getLogger(__name__)


def sync_permissions(db: Session) -> dict[str, Permission]:
    existing = {p.code: p for p in db.scalars(select(Permission))}
    for sort, (code, name, group) in enumerate(PERMISSIONS):
        p = existing.get(code)
        if p is None:
            p = Permission(code=code, name=name, group=group, sort=sort)
            db.add(p)
            existing[code] = p
        else:
            p.name, p.group, p.sort = name, group, sort
    db.flush()
    return existing


def sync_roles(db: Session, perms: dict[str, Permission]) -> None:
    for spec in BUILTIN_ROLES:
        role = db.scalar(select(Role).where(Role.code == spec["code"]))
        if role is None:
            role = Role(
                code=spec["code"],
                name=spec["name"],
                description=spec["description"],
                is_system=True,
                sort=spec["sort"],
            )
            role.permissions = [perms[c] for c in spec["permissions"]]
            db.add(role)
        elif spec["code"] == "super_admin":
            # 超级管理员始终拥有全部权限点（含新增的）
            role.permissions = list(perms.values())
            role.is_system = True
    db.flush()


def ensure_admin(db: Session) -> None:
    settings = get_settings()
    has_super = db.scalar(select(User.id).where(User.is_superuser.is_(True)).limit(1))
    if has_super:
        return
    password = settings.admin_password
    generated = not password
    if generated:
        password = secrets.token_urlsafe(12)
    admin = User(
        username=settings.admin_username,
        email=settings.admin_email,
        nickname="超级管理员",
        password_hash=hash_password(password),
        is_superuser=True,
        must_change_password=generated,
    )
    admin.roles = [db.scalar(select(Role).where(Role.code == "super_admin"))]
    db.add(admin)
    db.flush()
    if generated:
        log.warning("=" * 60)
        log.warning("已创建初始管理员 %s，随机密码：%s （首次登录需修改）", admin.username, password)
        log.warning("=" * 60)
    else:
        log.info("已创建初始管理员 %s", admin.username)


def bootstrap(db: Session) -> None:
    perms = sync_permissions(db)
    sync_roles(db, perms)
    ensure_admin(db)
    db.commit()
