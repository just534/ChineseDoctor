from sqlalchemy.orm import Session

from ..models import AuditLog, User


def record(
    db: Session,
    action: str,
    *,
    user: User | None = None,
    username: str | None = None,
    target: str = "",
    detail: str = "",
    ip: str = "",
    success: bool = True,
    commit: bool = True,
) -> None:
    db.add(
        AuditLog(
            user_id=user.id if user else None,
            username=username or (user.username if user else ""),
            action=action,
            target=target[:200],
            detail=detail[:2000],
            ip=ip,
            success=success,
        )
    )
    if commit:
        db.commit()
