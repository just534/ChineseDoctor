"""全文搜索、收藏、操作日志、控制台统计"""

import re
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user, get_optional_user, has_perm, require_perm
from ..models import AiUsage, AuditLog, Chapter, Document, Favorite, MedicalCase, Role, User
from ..schemas import AuditOut, FavoriteIn, FavoriteOut, Msg, Page, SearchHit

router = APIRouter()


def _snippet(text: str, word: str, radius: int = 60) -> str:
    plain = re.sub(r"[#*>|`_\-]+", " ", text)
    plain = re.sub(r"\s+", " ", plain)
    i = plain.lower().find(word.lower())
    if i < 0:
        return plain[: radius * 2].strip()
    start = max(0, i - radius)
    end = min(len(plain), i + len(word) + radius)
    return ("…" if start else "") + plain[start:end].strip() + ("…" if end < len(plain) else "")


@router.get("/search", response_model=list[SearchHit], tags=["搜索"])
def search(
    q: str = Query(min_length=1, max_length=50),
    scope: str = Query("all", pattern="^(all|documents|cases)$"),
    limit: int = Query(30, ge=1, le=100),
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    words = q.split()
    hits: list[SearchHit] = []
    if scope in ("all", "documents"):
        stmt = select(Chapter, Document).join(Document).where(Document.is_published.is_(True))
        for w in words:
            stmt = stmt.where(or_(Chapter.title.ilike(f"%{w}%"), Chapter.content.ilike(f"%{w}%")))
        # 标题命中优先
        title_hit = Chapter.title.ilike(f"%{words[0]}%")
        rows = db.execute(stmt.order_by(title_hit.desc(), Document.sort, Chapter.sort).limit(limit)).all()
        for ch, doc in rows:
            hits.append(
                SearchHit(
                    type="chapter",
                    id=ch.id,
                    title=ch.title,
                    subtitle=f"{doc.category} · {doc.title}",
                    snippet=_snippet(ch.content, words[0]),
                    document_slug=doc.slug,
                    chapter_id=ch.id,
                )
            )
    if scope in ("all", "cases") and has_perm(user, "case:read"):
        stmt = select(MedicalCase).where(MedicalCase.is_published.is_(True))
        for w in words:
            kw = f"%{w}%"
            stmt = stmt.where(
                or_(MedicalCase.diagnosis.ilike(kw), MedicalCase.prescription.ilike(kw), MedicalCase.pathogenesis.ilike(kw))
            )
        for c in db.scalars(stmt.order_by(MedicalCase.seq).limit(limit)):
            hits.append(
                SearchHit(
                    type="case",
                    id=c.id,
                    title=f"医案 #{c.seq} · {c.diagnosis[:40]}",
                    subtitle=" · ".join(x for x in (c.date_text, c.patient) if x),
                    snippet=_snippet(" ".join((c.pathogenesis, c.prescription, c.comment)), words[0]),
                )
            )
    return hits


# ---------------- 收藏 ----------------
@router.get("/favorites", response_model=list[FavoriteOut], tags=["收藏"])
def list_favorites(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    favs = db.scalars(select(Favorite).where(Favorite.user_id == user.id).order_by(Favorite.id.desc())).all()
    doc_ids = [f.target_id for f in favs if f.target_type == "document"]
    case_ids = [f.target_id for f in favs if f.target_type == "case"]
    docs = {d.id: d for d in db.scalars(select(Document).where(Document.id.in_(doc_ids)))} if doc_ids else {}
    cases = {c.id: c for c in db.scalars(select(MedicalCase).where(MedicalCase.id.in_(case_ids)))} if case_ids else {}
    out = []
    for f in favs:
        if f.target_type == "document" and (d := docs.get(f.target_id)):
            out.append(FavoriteOut(id=f.id, target_type="document", target_id=d.id, title=d.title,
                                   subtitle=d.slug, created_at=f.created_at))
        elif f.target_type == "case" and (c := cases.get(f.target_id)):
            out.append(FavoriteOut(id=f.id, target_type="case", target_id=c.id, title=f"医案 #{c.seq} · {c.diagnosis[:40]}",
                                   subtitle=c.date_text, created_at=f.created_at))
    return out


@router.post("/favorites", response_model=Msg, tags=["收藏"])
def add_favorite(body: FavoriteIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    model = Document if body.target_type == "document" else MedicalCase
    if body.target_type == "case" and not has_perm(user, "case:read"):
        raise HTTPException(403, "无权限：case:read")
    if not db.get(model, body.target_id):
        raise HTTPException(404, "收藏对象不存在")
    db.add(Favorite(user_id=user.id, target_type=body.target_type, target_id=body.target_id))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
    return Msg(message="已收藏")


@router.delete("/favorites", response_model=Msg, tags=["收藏"])
def remove_favorite(
    target_type: str = Query(pattern="^(document|case)$"),
    target_id: int = Query(),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    fav = db.scalar(
        select(Favorite).where(Favorite.user_id == user.id, Favorite.target_type == target_type, Favorite.target_id == target_id)
    )
    if fav:
        db.delete(fav)
        db.commit()
    return Msg(message="已取消收藏")


@router.get("/favorites/check", tags=["收藏"])
def check_favorite(
    target_type: str = Query(pattern="^(document|case)$"),
    target_id: int = Query(),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    exists = db.scalar(
        select(Favorite.id).where(Favorite.user_id == user.id, Favorite.target_type == target_type, Favorite.target_id == target_id)
    )
    return {"favorited": bool(exists)}


# ---------------- 操作日志 ----------------
@router.get("/audit-logs", response_model=Page[AuditOut], tags=["操作日志"])
def audit_logs(
    keyword: str = "",
    action: str = "",
    success: bool | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    _: User = Depends(require_perm("audit:read")),
    db: Session = Depends(get_db),
):
    q = select(AuditLog)
    if keyword:
        kw = f"%{keyword}%"
        q = q.where(or_(AuditLog.username.ilike(kw), AuditLog.target.ilike(kw), AuditLog.ip.ilike(kw), AuditLog.detail.ilike(kw)))
    if action:
        q = q.where(AuditLog.action.like(f"{action}%"))
    if success is not None:
        q = q.where(AuditLog.success.is_(success))
    total = db.scalar(select(func.count()).select_from(q.subquery()))
    items = db.scalars(q.order_by(AuditLog.id.desc()).offset((page - 1) * size).limit(size)).all()
    return Page(items=items, total=total, page=page, size=size)


# ---------------- 统计 ----------------
@router.get("/stats/public", tags=["统计"])
def public_stats(db: Session = Depends(get_db)):
    return {
        "documents": db.scalar(select(func.count(Document.id)).where(Document.is_published.is_(True))),
        "chapters": db.scalar(
            select(func.count(Chapter.id)).join(Document).where(Document.is_published.is_(True))
        ),
        "words": db.scalar(select(func.coalesce(func.sum(Document.word_count), 0)).where(Document.is_published.is_(True))),
        "cases": db.scalar(select(func.count(MedicalCase.id)).where(MedicalCase.is_published.is_(True))),
    }


@router.get("/stats/dashboard", tags=["统计"])
def dashboard(_: User = Depends(require_perm("dashboard:view")), db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    days = [(now - timedelta(days=i)).date() for i in range(6, -1, -1)]
    logins = db.execute(
        select(AuditLog.created_at).where(AuditLog.action == "login", AuditLog.success.is_(True), AuditLog.created_at >= week_ago)
    ).scalars().all()
    regs = db.execute(select(User.created_at).where(User.created_at >= week_ago)).scalars().all()

    def bucket(values):
        counts = {d: 0 for d in days}
        for v in values:
            d = (v if v.tzinfo else v.replace(tzinfo=timezone.utc)).date()
            if d in counts:
                counts[d] += 1
        return [counts[d] for d in days]

    top_docs = db.execute(select(Document.title, Document.view_count).order_by(Document.view_count.desc()).limit(8)).all()
    recent = db.scalars(select(AuditLog).order_by(AuditLog.id.desc()).limit(10)).all()
    role_dist = db.execute(
        select(Role.name, func.count(User.id)).join(Role.users).group_by(Role.name)
    ).all()
    return {
        "users": db.scalar(select(func.count(User.id))),
        "active_users": db.scalar(select(func.count(User.id)).where(User.is_active.is_(True))),
        "new_users_week": len(regs),
        "documents": db.scalar(select(func.count(Document.id))),
        "cases": db.scalar(select(func.count(MedicalCase.id))),
        "ai_calls_today": db.scalar(
            select(func.coalesce(func.sum(AiUsage.count), 0)).where(AiUsage.day == now.date().isoformat())
        ),
        "trend": {
            "days": [d.strftime("%m-%d") for d in days],
            "logins": bucket(logins),
            "registrations": bucket(regs),
        },
        "top_documents": [{"title": t, "views": v} for t, v in top_docs],
        "role_distribution": [{"name": n, "count": c} for n, c in role_dist],
        "recent_logs": [AuditOut.model_validate(r).model_dump() for r in recent],
    }
