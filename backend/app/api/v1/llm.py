# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/28 18:31
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import success_response
from app.db.session import get_db_session
from app.llm.gateway import build_model_gateway
from app.llm.schemas import ChatRequest, EmbeddingRequest
from app.services.model_call_log_service import ModelCallLogService

router = APIRouter()


def get_request_id(request: Request, fallback: str | None = None) -> str | None:
    return getattr(request.state, "request_id", None) or fallback


@router.post("/chat")
async def chat(
        payload: ChatRequest,
        request: Request,
        db_session: AsyncSession = Depends(get_db_session),
):
    request_id = get_request_id(request, payload.request_id)
    payload = payload.model_copy(update={"request_id": request_id})

    gateway = build_model_gateway(
        log_service=ModelCallLogService(db_session),
    )
    result = await gateway.chat(payload)

    return success_response(
        data=result.model_dump(mode="json"),
        request_id=request_id,
    )


@router.post("/embeddings")
async def embeddings(
        payload: EmbeddingRequest,
        request: Request,
        db_session: AsyncSession = Depends(get_db_session),
):
    request_id = get_request_id(request, payload.request_id)
    payload = payload.model_copy(update={"request_id": request_id})

    gateway = build_model_gateway(
        log_service=ModelCallLogService(db_session),
    )
    result = await gateway.embeddings(payload)

    return success_response(
        data=result.model_dump(mode="json"),
        request_id=request_id,
    )


@router.post("/chat/stream")
async def stream_chat(
        payload: ChatRequest,
        request: Request,
        db_session: AsyncSession = Depends(get_db_session),
):
    """
    SSE 流式输出测试接口。

    本接口返回 text/event-stream，不走普通 JSON 包裹。
    原因：SSE 协议要求持续返回 data: xxx 格式的事件流。
    但仍然返回 X-Request-ID，满足请求追踪要求。
    """
    request_id = get_request_id(request, payload.request_id)
    payload = payload.model_copy(update={"request_id": request_id})

    gateway = build_model_gateway(
        log_service=ModelCallLogService(db_session),
    )

    async def event_generator():
        async for chunk in gateway.stream_chat(payload):
            yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "X-Request-ID": request_id or "",
        },
    )
