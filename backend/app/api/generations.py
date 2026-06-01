import asyncio
import json
import time
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import PlainTextResponse, StreamingResponse
from pydantic import ValidationError
from sqlalchemy.orm import Session
from app.api.deps import get_current_user
from app.core.config import get_settings
from app.db.session import SessionLocal, get_db
from app.models.entities import Generation, ModelCallLog, User
from app.schemas.generation import GenerationDetail, GenerationListItem, GenerationRequest
from app.services.ai_provider import ProviderError, get_ai_provider
from app.services.generation_runtime import input_snapshot, sse_event
from app.services.markdown import generation_to_markdown
from app.services.quota import QuotaExceeded, deduct_quota, refund_quota
from app.services.redis_client import get_redis


router = APIRouter(prefix="/generations", tags=["generations"])


async def acquire_generation_lock(user_id: int) -> str | None:
    redis = await get_redis()
    if redis is None:
        return None
    settings = get_settings()
    key = f"generation-lock:{user_id}"
    locked = await redis.set(key, "1", ex=settings.generation_lock_seconds, nx=True)
    return key if locked else ""


async def release_generation_lock(key: str | None) -> None:
    if not key:
        return
    redis = await get_redis()
    if redis is not None:
        await redis.delete(key)


@router.post("/stream")
async def stream_generation(payload: GenerationRequest, current_user: User = Depends(get_current_user)):
    try:
        provider = get_ai_provider()
    except ProviderError as exc:
        raise HTTPException(status_code=400, detail=exc.code) from exc
    lock_key = await acquire_generation_lock(current_user.id)
    if lock_key == "":
        raise HTTPException(status_code=409, detail="GENERATION_IN_PROGRESS")

    db = SessionLocal()
    generation = Generation(
        user_id=current_user.id,
        tool_type=payload.tool_type,
        mode=payload.mode,
        input_snapshot=input_snapshot(payload),
        config_snapshot=payload.config,
        status="running",
    )
    try:
        quota = deduct_quota(db, current_user.id)
        db.add(generation)
        db.flush()
        generation_id = generation.id
        db.commit()
    except QuotaExceeded as exc:
        db.rollback()
        await release_generation_lock(lock_key)
        db.close()
        raise HTTPException(status_code=402, detail="QUOTA_EXCEEDED") from exc
    except Exception:
        db.rollback()
        await release_generation_lock(lock_key)
        db.close()
        raise

    async def event_stream() -> AsyncGenerator[str, None]:
        start = time.perf_counter()
        output_parts: list[str] = []
        local_db = db
        try:
            yield sse_event("metadata", {"generation_id": generation_id, **quota})
            async for chunk in provider.stream_text(payload):
                output_parts.append(chunk)
                yield sse_event("delta", {"text": chunk})
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            full_output = "".join(output_parts)
            item = local_db.get(Generation, generation_id)
            if item:
                item.output_content = full_output
                item.status = "succeeded"
                item.elapsed_ms = elapsed_ms
                item.completed_at = datetime.now(timezone.utc)
                item.completion_tokens = max(len(full_output) // 2, 1)
                local_db.add(
                    ModelCallLog(
                        generation_id=generation_id,
                        provider=provider.name,
                        model=provider.model,
                        prompt_tokens=max(len(json.dumps(input_snapshot(payload), ensure_ascii=False)) // 2, 1),
                        completion_tokens=item.completion_tokens,
                        status="succeeded",
                    )
                )
                local_db.commit()
            yield sse_event("usage", {"completion_tokens": max(len(full_output) // 2, 1), "elapsed_ms": elapsed_ms})
            yield sse_event("done", {"generation_id": generation_id})
        except (ProviderError, asyncio.CancelledError) as exc:
            local_db.rollback()
            item = local_db.get(Generation, generation_id)
            code = exc.code if isinstance(exc, ProviderError) else "CLIENT_DISCONNECTED"
            message = exc.message if isinstance(exc, ProviderError) else "客户端已断开连接。"
            if item:
                item.status = "failed"
                item.error_code = code
                item.error_message = message
                item.completed_at = datetime.now(timezone.utc)
            # Provider/client failures should not burn the user's daily quota.
            refund_quota(local_db, current_user.id)
            local_db.add(
                ModelCallLog(
                    generation_id=generation_id,
                    provider=provider.name,
                    model=provider.model,
                    status="failed",
                )
            )
            local_db.commit()
            if isinstance(exc, asyncio.CancelledError):
                raise
            yield sse_event("error", {"code": code, "message": message})
        except Exception:
            local_db.rollback()
            item = local_db.get(Generation, generation_id)
            if item:
                item.status = "failed"
                item.error_code = "INTERNAL_ERROR"
                item.error_message = "生成失败，请稍后重试。"
                item.completed_at = datetime.now(timezone.utc)
            # Unexpected streaming failures are compensated here after rollback.
            refund_quota(local_db, current_user.id)
            local_db.commit()
            yield sse_event("error", {"code": "INTERNAL_ERROR", "message": "生成失败，请稍后重试。"})
        finally:
            await release_generation_lock(lock_key)
            local_db.close()

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("", response_model=list[GenerationListItem])
def list_generations(
    limit: int = 10,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    limit = min(max(limit, 1), 10)
    return (
        db.query(Generation)
        .filter(Generation.user_id == current_user.id, Generation.tool_type.in_(["humanize", "aigc_reduce", "generate"]))
        .order_by(Generation.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.get("/{generation_id}", response_model=GenerationDetail)
def get_generation(generation_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = db.get(Generation, generation_id)
    if not item or item.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="GENERATION_NOT_FOUND")
    return item


@router.delete("/{generation_id}", status_code=204)
def delete_generation(generation_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = db.get(Generation, generation_id)
    if not item or item.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="GENERATION_NOT_FOUND")
    db.query(ModelCallLog).filter(ModelCallLog.generation_id == generation_id).delete(synchronize_session=False)
    db.delete(item)
    db.commit()
    return Response(status_code=204)


@router.post("/{generation_id}/export-markdown", response_class=PlainTextResponse)
def export_markdown(generation_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = db.get(Generation, generation_id)
    if not item or item.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="GENERATION_NOT_FOUND")
    return PlainTextResponse(generation_to_markdown(item), media_type="text/markdown; charset=utf-8")
