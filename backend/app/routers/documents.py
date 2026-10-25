from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import client_ip, get_optional_user, has_perm, require_perm
from ..models import Chapter, Document, User
from ..schemas import (
    ChapterIn,
    ChapterOut,
    DocumentCreate,
    DocumentDetail,
    DocumentOut,
    DocumentUpdate,
    Msg,
)
from ..services import audit
from ..services.importer import CATEGORIES, count_words

router = APIRouter(tags=["典籍"])


def _chapter_counts(db: Session, ids: list[int]) -> dict[int, int]:
    if not ids:
        return {}
    rows = db.execute(
        select(Chapter.document_id, func.count(Chapter.id)).where(Chapter.document_id.in_(ids)).group_by(Chapter.document_id)
    )
    return dict(rows.all())


def _doc_out(doc: Document, chapter_count: int) -> DocumentOut:
    out = DocumentOut.model_validate(doc)
    out.chapter_count = chapter_count
    return out


def _get_doc(db: Session, slug_or_id: str, user: User | None) -> Document:
    q = select(Document)
    q = q.where(Document.id == int(slug_or_id)) if slug_or_id.isdigit() else q.where(Document.slug == slug_or_id)
    doc = db.scalar(q)
    if not doc or (not doc.is_published and not has_perm(user, "document:manage")):
        raise HTTPException(404, "典籍不存在")
    return doc


def _recount(db: Session, doc: Document) -> None:
    db.flush()
    doc.word_count = db.scalar(select(func.coalesce(func.sum(Chapter.word_count), 0)).where(Chapter.document_id == doc.id))


@router.get("/documents/categories")
def categories(db: Session = Depends(get_db)):
    rows = dict(
        db.execute(
            select(Document.category, func.count(Document.id)).where(Document.is_published.is_(True)).group_by(Document.category)
        ).all()
    )
    ordered = [c for c in CATEGORIES if c in rows] + sorted(c for c in rows if c not in CATEGORIES)
    return [{"name": c, "count": rows[c]} for c in ordered]


@router.get("/documents", response_model=list[DocumentOut])
def list_documents(
    category: str | None = None,
    keyword: str = "",
    include_unpublished: bool = False,
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    q = select(Document)
    if not (include_unpublished and has_perm(user, "document:manage")):
        q = q.where(Document.is_published.is_(True))
    if category:
        q = q.where(Document.category == category)
    if keyword:
        kw = f"%{keyword.strip()}%"
        q = q.where(or_(Document.title.ilike(kw), Document.summary.ilike(kw)))
    docs = db.scalars(q.order_by(Document.sort, Document.id)).all()
    counts = _chapter_counts(db, [d.id for d in docs])
    return [_doc_out(d, counts.get(d.id, 0)) for d in docs]


@router.get("/documents/{slug}", response_model=DocumentDetail)
def get_document(slug: str, user: User | None = Depends(get_optional_user), db: Session = Depends(get_db)):
    doc = _get_doc(db, slug, user)
    db.execute(update(Document).where(Document.id == doc.id).values(view_count=Document.view_count + 1))
    db.commit()
    db.refresh(doc)
    out = DocumentDetail.model_validate(doc)
    out.chapter_count = len(doc.chapters)
    return out


@router.get("/documents/{slug}/chapters/{chapter_id}")
def get_chapter(slug: str, chapter_id: int, user: User | None = Depends(get_optional_user), db: Session = Depends(get_db)):
    doc = _get_doc(db, slug, user)
    ch = db.get(Chapter, chapter_id)
    if not ch or ch.document_id != doc.id:
        raise HTTPException(404, "章节不存在")
    ids = [c.id for c in doc.chapters]
    i = ids.index(ch.id)
    return {
        **ChapterOut.model_validate(ch).model_dump(),
        "prev_id": ids[i - 1] if i > 0 else None,
        "next_id": ids[i + 1] if i < len(ids) - 1 else None,
    }


# ---------------- 管理 ----------------
@router.post("/documents", response_model=DocumentOut, status_code=201)
def create_document(
    body: DocumentCreate, request: Request, actor: User = Depends(require_perm("document:manage")), db: Session = Depends(get_db)
):
    if db.scalar(select(Document.id).where(Document.slug == body.slug)):
        raise HTTPException(status.HTTP_409_CONFLICT, "标识已存在")
    doc = Document(**body.model_dump(), updated_by=actor.id)
    db.add(doc)
    db.flush()
    audit.record(db, "document.create", user=actor, target=doc.title, ip=client_ip(request))
    return _doc_out(doc, 0)


@router.put("/documents/{doc_id}", response_model=DocumentOut)
def update_document(
    doc_id: int,
    body: DocumentUpdate,
    request: Request,
    actor: User = Depends(require_perm("document:manage")),
    db: Session = Depends(get_db),
):
    doc = db.get(Document, doc_id)
    if not doc:
        raise HTTPException(404, "典籍不存在")
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(doc, k, v)
    doc.updated_by = actor.id
    audit.record(db, "document.update", user=actor, target=doc.title, detail=",".join(data), ip=client_ip(request))
    return _doc_out(doc, len(doc.chapters))


@router.delete("/documents/{doc_id}", response_model=Msg)
def delete_document(
    doc_id: int, request: Request, actor: User = Depends(require_perm("document:manage")), db: Session = Depends(get_db)
):
    doc = db.get(Document, doc_id)
    if not doc:
        raise HTTPException(404, "典籍不存在")
    title = doc.title
    db.delete(doc)
    audit.record(db, "document.delete", user=actor, target=title, ip=client_ip(request))
    return Msg(message="已删除")


@router.post("/documents/{doc_id}/chapters", response_model=ChapterOut, status_code=201)
def create_chapter(
    doc_id: int,
    body: ChapterIn,
    request: Request,
    actor: User = Depends(require_perm("document:manage")),
    db: Session = Depends(get_db),
):
    doc = db.get(Document, doc_id)
    if not doc:
        raise HTTPException(404, "典籍不存在")
    sort = body.sort if body.sort is not None else (max((c.sort for c in doc.chapters), default=-1) + 1)
    ch = Chapter(document_id=doc.id, title=body.title, content=body.content, word_count=count_words(body.content), sort=sort)
    db.add(ch)
    _recount(db, doc)
    doc.updated_by = actor.id
    audit.record(db, "chapter.create", user=actor, target=f"{doc.title} / {ch.title}", ip=client_ip(request))
    return ch


@router.put("/chapters/{chapter_id}", response_model=ChapterOut)
def update_chapter(
    chapter_id: int,
    body: ChapterIn,
    request: Request,
    actor: User = Depends(require_perm("document:manage")),
    db: Session = Depends(get_db),
):
    ch = db.get(Chapter, chapter_id)
    if not ch:
        raise HTTPException(404, "章节不存在")
    ch.title = body.title
    ch.content = body.content
    ch.word_count = count_words(body.content)
    if body.sort is not None:
        ch.sort = body.sort
    doc = ch.document
    _recount(db, doc)
    doc.updated_by = actor.id
    audit.record(db, "chapter.update", user=actor, target=f"{doc.title} / {ch.title}", ip=client_ip(request))
    return ch


@router.delete("/chapters/{chapter_id}", response_model=Msg)
def delete_chapter(
    chapter_id: int, request: Request, actor: User = Depends(require_perm("document:manage")), db: Session = Depends(get_db)
):
    ch = db.get(Chapter, chapter_id)
    if not ch:
        raise HTTPException(404, "章节不存在")
    doc = ch.document
    target = f"{doc.title} / {ch.title}"
    db.delete(ch)
    _recount(db, doc)
    audit.record(db, "chapter.delete", user=actor, target=target, ip=client_ip(request))
    return Msg(message="已删除")
