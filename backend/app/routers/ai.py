import json
import logging
from datetime import datetime, timezone

import anthropic
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import SessionLocal, get_db
from ..deps import client_ip, require_perm
from ..models import AiUsage, User
from ..schemas import ChatIn
from ..services import ai, audit

router = APIRouter(prefix="/ai", tags=["AI 问诊"])
settings = get_settings()
log = logging.getLogger(__name__)


def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _usage_row(db: Session, user_id: int) -> AiUsage:
    row = db.scalar(select(AiUsage).where(AiUsage.user_id == user_id, AiUsage.day == _today()))
    if not row:
        row = AiUsage(user_id=user_id, day=_today(), count=0)
        db.add(row)
        db.flush()
    return row


@router.get("/quota")
def quota(user: User = Depends(require_perm("ai:chat")), db: Session = Depends(get_db)):
    row = db.scalar(select(AiUsage).where(AiUsage.user_id == user.id, AiUsage.day == _today()))
    used = row.count if row else 0
    return {
        "enabled": settings.ai_enabled,
        "used": used,
        "limit": None if user.is_superuser else settings.ai_daily_limit,
    }


def _sse(event: str, data) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/chat")
def chat(body: ChatIn, request: Request, user: User = Depends(require_perm("ai:chat")), db: Session = Depends(get_db)):
    if not settings.ai_enabled:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "AI 问诊未启用，请管理员配置 ANTHROPIC_API_KEY")
    if body.messages[-1].role != "user":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "最后一条消息必须来自用户")
    row = _usage_row(db, user.id)
    if not user.is_superuser and row.count >= settings.ai_daily_limit:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, f"今日问诊次数已用完（{settings.ai_daily_limit} 次）")
    row.count += 1
    audit.record(db, "ai.chat", user=user, ip=client_ip(request), detail=body.messages[-1].content[:200])

    history = [m.model_dump() for m in body.messages]
    refs = ai.retrieve(db, history[-1]["content"])
    messages = ai.build_messages(history, refs)
    user_id = user.id

    def gen():
        yield _sse("refs", [{k: r[k] for k in ("chapter_id", "title", "document", "slug")} for r in refs])
        usage: dict = {}
        try:
            for text in ai.stream_answer(messages, usage):
                yield _sse("delta", text)
            if usage.get("stop_reason") == "refusal":
                yield _sse("error", "该问题无法回答，请换个问法。")
            yield _sse("done", {"output_tokens": usage.get("output_tokens", 0)})
        except anthropic.RateLimitError:
            yield _sse("error", "AI 服务繁忙，请稍后再试")
        except anthropic.APIConnectionError:
            yield _sse("error", "无法连接 AI 服务")
        except anthropic.APIStatusError as e:
            log.exception("AI 调用失败")
            yield _sse("error", f"AI 服务异常（{e.status_code}）")
        finally:
            if usage:
                with SessionLocal() as s:
                    r = s.scalar(select(AiUsage).where(AiUsage.user_id == user_id, AiUsage.day == _today()))
                    if r:
                        r.input_tokens += usage.get("input_tokens", 0)
                        r.output_tokens += usage.get("output_tokens", 0)
                        s.commit()

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
