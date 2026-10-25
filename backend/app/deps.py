from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .db import get_db
from .models import User
from .security import decode_token

bearer = HTTPBearer(auto_error=False)


def client_ip(request: Request) -> str:
    # uvicorn runs with --proxy-headers behind nginx, so client.host is the real address
    return request.client.host if request.client else ""


def _resolve_user(creds: HTTPAuthorizationCredentials | None, db: Session) -> User | None:
    if not creds:
        return None
    payload = decode_token(creds.credentials, "access")
    if not payload:
        return None
    user = db.get(User, int(payload["sub"]))
    if not user or not user.is_active or user.token_version != payload.get("ver"):
        return None
    return user


def get_optional_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)
) -> User | None:
    return _resolve_user(creds, db)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)
) -> User:
    user = _resolve_user(creds, db)
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "登录已失效，请重新登录")
    return user


def has_perm(user: User | None, code: str) -> bool:
    if not user:
        return False
    return user.is_superuser or code in user.permission_codes


def require_perm(*codes: str) -> Callable[..., User]:
    """要求当前用户拥有全部给定权限点。"""

    def checker(user: User = Depends(get_current_user)) -> User:
        if user.must_change_password:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "请先修改初始密码")
        missing = [c for c in codes if not has_perm(user, c)]
        if missing:
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"无权限：{', '.join(missing)}")
        return user

    return checker
