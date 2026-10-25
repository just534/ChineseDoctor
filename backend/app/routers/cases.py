from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import client_ip, has_perm, require_perm
from ..models import MedicalCase, User
from ..schemas import CaseIn, CaseOut, Msg, Page
from ..services import audit

router = APIRouter(prefix="/cases", tags=["医案"])

SEARCH_FIELDS = {
    "all": None,
    "diagnosis": MedicalCase.diagnosis,
    "prescription": MedicalCase.prescription,
    "pathogenesis": MedicalCase.pathogenesis,
    "acupuncture": MedicalCase.acupuncture,
    "comment": MedicalCase.comment,
}


@router.get("", response_model=Page[CaseOut])
def list_cases(
    keyword: str = "",
    field: str = Query("all", pattern="^(all|diagnosis|prescription|pathogenesis|acupuncture|comment)$"),
    year: int | None = None,
    include_unpublished: bool = False,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    user: User = Depends(require_perm("case:read")),
    db: Session = Depends(get_db),
):
    q = select(MedicalCase)
    if not (include_unpublished and has_perm(user, "case:manage")):
        q = q.where(MedicalCase.is_published.is_(True))
    for word in keyword.split():
        kw = f"%{word}%"
        col = SEARCH_FIELDS[field]
        if col is not None:
            q = q.where(col.ilike(kw))
        else:
            q = q.where(
                or_(
                    MedicalCase.diagnosis.ilike(kw),
                    MedicalCase.pathogenesis.ilike(kw),
                    MedicalCase.prescription.ilike(kw),
                    MedicalCase.acupuncture.ilike(kw),
                    MedicalCase.patient.ilike(kw),
                    MedicalCase.comment.ilike(kw),
                    MedicalCase.outcome.ilike(kw),
                )
            )
    if year:
        q = q.where(MedicalCase.year == year)
    total = db.scalar(select(func.count()).select_from(q.subquery()))
    items = db.scalars(q.order_by(MedicalCase.seq).offset((page - 1) * size).limit(size)).all()
    return Page(items=items, total=total, page=page, size=size)


@router.get("/years")
def case_years(_: User = Depends(require_perm("case:read")), db: Session = Depends(get_db)):
    rows = db.execute(
        select(MedicalCase.year, func.count(MedicalCase.id))
        .where(MedicalCase.year.is_not(None), MedicalCase.is_published.is_(True))
        .group_by(MedicalCase.year)
        .order_by(MedicalCase.year)
    ).all()
    return [{"year": y, "count": c} for y, c in rows]


@router.get("/{case_id}", response_model=CaseOut)
def get_case(case_id: int, user: User = Depends(require_perm("case:read")), db: Session = Depends(get_db)):
    c = db.get(MedicalCase, case_id)
    if not c or (not c.is_published and not has_perm(user, "case:manage")):
        raise HTTPException(404, "医案不存在")
    return c


@router.post("", response_model=CaseOut, status_code=201)
def create_case(
    body: CaseIn, request: Request, actor: User = Depends(require_perm("case:manage")), db: Session = Depends(get_db)
):
    data = body.model_dump()
    if data["seq"] is None:
        data["seq"] = (db.scalar(select(func.max(MedicalCase.seq))) or 0) + 1
    c = MedicalCase(**data)
    db.add(c)
    db.flush()
    audit.record(db, "case.create", user=actor, target=f"#{c.seq} {c.diagnosis[:50]}", ip=client_ip(request))
    return c


@router.put("/{case_id}", response_model=CaseOut)
def update_case(
    case_id: int,
    body: CaseIn,
    request: Request,
    actor: User = Depends(require_perm("case:manage")),
    db: Session = Depends(get_db),
):
    c = db.get(MedicalCase, case_id)
    if not c:
        raise HTTPException(404, "医案不存在")
    for k, v in body.model_dump(exclude_unset=True).items():
        if k == "seq" and v is None:
            continue
        setattr(c, k, v)
    audit.record(db, "case.update", user=actor, target=f"#{c.seq} {c.diagnosis[:50]}", ip=client_ip(request))
    return c


@router.delete("/{case_id}", response_model=Msg)
def delete_case(
    case_id: int, request: Request, actor: User = Depends(require_perm("case:manage")), db: Session = Depends(get_db)
):
    c = db.get(MedicalCase, case_id)
    if not c:
        raise HTTPException(404, "医案不存在")
    target = f"#{c.seq} {c.diagnosis[:50]}"
    db.delete(c)
    audit.record(db, "case.delete", user=actor, target=target, ip=client_ip(request))
    return Msg(message="已删除")
