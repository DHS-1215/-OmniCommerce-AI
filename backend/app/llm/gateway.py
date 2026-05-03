# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/28 18:17
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
import time
from collections.abc import AsyncIterator
from typing import Any

from app.core.config import Settings, get_settings
from app.core.exceptions import ModelGatewayException
from app.llm.router import ModelProviderRouter, build_default_provider_router
from app.llm.schemas import ChatRequest, ChatResponse, EmbeddingRequest, EmbeddingResponse
from app.services.model_call_log_service import ModelCallLogService


def truncate_text(text: str | None, max_length: int = 500) -> str | None:
    """
    日志摘要截断。

    禁止把完整 Prompt、完整用户隐私、完整模型输出写入日志。
    """
    if text is None:
        return None

    normalized = text.strip()
    if len(normalized) <= max_length:
        return normalized

    return normalized[:max_length] + "...[truncated]"


def summarize_messages(request: ChatRequest) -> str:
    joined = "\n".join(
        f"{message.role}: {message.content}"
        for message in request.messages
    )
    return truncate_text(joined) or ""


def summarize_texts(request: EmbeddingRequest) -> str:
    joined = "\n".join(request.texts)
    return truncate_text(joined) or ""


def get_retry_count(exc: ModelGatewayException) -> int | None:
    if not exc.data:
        return None

    retry_count = exc.data.get("retry_count")
    if isinstance(retry_count, int):
        return retry_count

    return None


class ModelGateway:
    """
    统一模型网关。

    后续所有 LLM / Embedding 调用都应该从这里进入。
    """

    def __init__(
            self,
            provider_router: ModelProviderRouter,
            log_service: ModelCallLogService | Any,
            settings: Settings | None = None,
    ) -> None:
        self.provider_router = provider_router
        self.log_service = log_service
        self.settings = settings or get_settings()

    async def chat(self, request: ChatRequest) -> ChatResponse:
        provider = self.provider_router.get_chat_provider(request.provider)
        model_name = request.model or self.settings.default_llm_model
        start = time.perf_counter()

        try:
            response = await provider.chat(
                request.model_copy(update={"model": model_name})
            )

            await self.log_service.create_log(
                tenant_id=request.tenant_id,
                request_id=request.request_id,
                user_id=request.user_id,
                provider=response.provider,
                model_name=response.model_name,
                model_type="llm",
                call_type="chat",
                prompt_template_id=request.prompt_template_id,
                prompt_version_id=request.prompt_version_id,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                total_tokens=response.usage.total_tokens,
                latency_ms=response.latency_ms,
                status="success",
                input_summary=summarize_messages(request),
                output_summary=truncate_text(response.content),
                metadata_json={
                    "raw_response_id": response.raw_response_id,
                    "retry_count": 0,
                },
            )

            return response

        except ModelGatewayException as exc:
            latency_ms = int((time.perf_counter() - start) * 1000)
            await self.log_service.create_log(
                tenant_id=request.tenant_id,
                request_id=request.request_id,
                user_id=request.user_id,
                provider=request.provider or self.settings.default_llm_provider,
                model_name=model_name,
                model_type="llm",
                call_type="chat",
                prompt_template_id=request.prompt_template_id,
                prompt_version_id=request.prompt_version_id,
                latency_ms=latency_ms,
                status="failed",
                error_code=exc.code,
                error_message=truncate_text(exc.message),
                input_summary=summarize_messages(request),
                metadata_json={
                    "retry_count": get_retry_count(exc),
                },
            )
            raise

        except Exception as exc:
            latency_ms = int((time.perf_counter() - start) * 1000)
            await self.log_service.create_log(
                tenant_id=request.tenant_id,
                request_id=request.request_id,
                user_id=request.user_id,
                provider=request.provider or self.settings.default_llm_provider,
                model_name=model_name,
                model_type="llm",
                call_type="chat",
                prompt_template_id=request.prompt_template_id,
                prompt_version_id=request.prompt_version_id,
                latency_ms=latency_ms,
                status="failed",
                error_code="MODEL_CALL_FAILED",
                error_message=truncate_text(str(exc)),
                input_summary=summarize_messages(request),
            )
            raise ModelGatewayException(
                code="MODEL_CALL_FAILED",
                message="Model call failed",
            ) from exc

    async def embeddings(self, request: EmbeddingRequest) -> EmbeddingResponse:
        provider = self.provider_router.get_embedding_provider(request.provider)
        model_name = request.model or self.settings.default_embedding_model
        start = time.perf_counter()

        try:
            response = await provider.embeddings(
                request.model_copy(update={"model": model_name})
            )

            await self.log_service.create_log(
                tenant_id=request.tenant_id,
                request_id=request.request_id,
                user_id=request.user_id,
                provider=response.provider,
                model_name=response.model_name,
                model_type="embedding",
                call_type="embedding",
                prompt_template_id=request.prompt_template_id,
                prompt_version_id=request.prompt_version_id,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                total_tokens=response.usage.total_tokens,
                latency_ms=response.latency_ms,
                status="success",
                input_summary=summarize_texts(request),
                output_summary=f"embedding_count={len(response.embeddings)}",
                metadata_json={
                    "raw_response_id": response.raw_response_id,
                    "embedding_count": len(response.embeddings),
                    "retry_count": 0,
                },
            )

            return response

        except ModelGatewayException as exc:
            latency_ms = int((time.perf_counter() - start) * 1000)
            await self.log_service.create_log(
                tenant_id=request.tenant_id,
                request_id=request.request_id,
                user_id=request.user_id,
                provider=request.provider or self.settings.default_embedding_provider,
                model_name=model_name,
                model_type="embedding",
                call_type="embedding",
                prompt_template_id=request.prompt_template_id,
                prompt_version_id=request.prompt_version_id,
                latency_ms=latency_ms,
                status="failed",
                error_code=exc.code,
                error_message=truncate_text(exc.message),
                input_summary=summarize_texts(request),
                metadata_json={
                    "retry_count": get_retry_count(exc),
                },
            )
            raise

        except Exception as exc:
            latency_ms = int((time.perf_counter() - start) * 1000)
            await self.log_service.create_log(
                tenant_id=request.tenant_id,
                request_id=request.request_id,
                user_id=request.user_id,
                provider=request.provider or self.settings.default_embedding_provider,
                model_name=model_name,
                model_type="embedding",
                call_type="embedding",
                prompt_template_id=request.prompt_template_id,
                prompt_version_id=request.prompt_version_id,
                latency_ms=latency_ms,
                status="failed",
                error_code="MODEL_EMBEDDING_CALL_FAILED",
                error_message=truncate_text(str(exc)),
                input_summary=summarize_texts(request),
            )
            raise ModelGatewayException(
                code="MODEL_EMBEDDING_CALL_FAILED",
                message="Model embedding call failed",
            ) from exc

    async def stream_chat(self, request: ChatRequest) -> AsyncIterator[str]:
        provider = self.provider_router.get_chat_provider(request.provider)
        model_name = request.model or self.settings.default_llm_model
        start = time.perf_counter()
        chunks: list[str] = []

        try:
            async for chunk in provider.stream_chat(
                    request.model_copy(update={"model": model_name})
            ):
                chunks.append(chunk)
                yield chunk

            latency_ms = int((time.perf_counter() - start) * 1000)
            await self.log_service.create_log(
                tenant_id=request.tenant_id,
                request_id=request.request_id,
                user_id=request.user_id,
                provider=provider.provider_name,
                model_name=model_name,
                model_type="llm",
                call_type="stream_chat",
                prompt_template_id=request.prompt_template_id,
                prompt_version_id=request.prompt_version_id,
                latency_ms=latency_ms,
                status="success",
                input_summary=summarize_messages(request),
                output_summary=truncate_text("".join(chunks)),
                metadata_json={
                    "stream": True,
                    "chunk_count": len(chunks),
                    "retry_count": 0,
                },
            )

        except ModelGatewayException as exc:
            latency_ms = int((time.perf_counter() - start) * 1000)
            await self.log_service.create_log(
                tenant_id=request.tenant_id,
                request_id=request.request_id,
                user_id=request.user_id,
                provider=request.provider or self.settings.default_llm_provider,
                model_name=model_name,
                model_type="llm",
                call_type="stream_chat",
                prompt_template_id=request.prompt_template_id,
                prompt_version_id=request.prompt_version_id,
                latency_ms=latency_ms,
                status="failed",
                error_code=exc.code,
                error_message=truncate_text(exc.message),
                input_summary=summarize_messages(request),
                output_summary=truncate_text("".join(chunks)) if chunks else None,
                metadata_json={
                    "stream": True,
                    "chunk_count": len(chunks),
                    "retry_count": get_retry_count(exc),
                },
            )
            raise


def build_model_gateway(log_service: ModelCallLogService) -> ModelGateway:
    settings = get_settings()
    provider_router = build_default_provider_router(settings=settings)
    return ModelGateway(
        provider_router=provider_router,
        log_service=log_service,
        settings=settings,
    )
