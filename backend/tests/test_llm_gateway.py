# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/28 18:18
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
import uuid
from collections.abc import AsyncIterator

import pytest

from app.core.exceptions import ModelGatewayException
from app.llm.base import BaseModelProvider
from app.llm.gateway import ModelGateway, truncate_text
from app.llm.router import ModelProviderRouter
from app.llm.schemas import (
    ChatRequest,
    ChatResponse,
    EmbeddingRequest,
    EmbeddingResponse,
    LLMMessage,
    TokenUsage,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


class FakeProvider(BaseModelProvider):
    provider_name = "fake"

    async def chat(self, request: ChatRequest) -> ChatResponse:
        return ChatResponse(
            provider=self.provider_name,
            model_name=request.model or "fake-chat-model",
            content="fake answer",
            usage=TokenUsage(
                input_tokens=3,
                output_tokens=2,
                total_tokens=5,
            ),
            latency_ms=12,
            raw_response_id="resp_fake_001",
        )

    async def embeddings(self, request: EmbeddingRequest) -> EmbeddingResponse:
        return EmbeddingResponse(
            provider=self.provider_name,
            model_name=request.model or "fake-embedding-model",
            embeddings=[[0.1, 0.2, 0.3] for _ in request.texts],
            usage=TokenUsage(
                input_tokens=4,
                output_tokens=0,
                total_tokens=4,
            ),
            latency_ms=8,
            raw_response_id="emb_fake_001",
        )

    async def stream_chat(self, request: ChatRequest) -> AsyncIterator[str]:
        yield "hello"
        yield " "
        yield "world"


class FailedProvider(FakeProvider):
    async def chat(self, request: ChatRequest) -> ChatResponse:
        raise ModelGatewayException(
            code="MODEL_PROVIDER_TIMEOUT",
            message="timeout",
            data={
                "retry_count": 2,
            },
        )


class MemoryLogService:
    def __init__(self) -> None:
        self.records: list[dict] = []

    async def create_log(self, **kwargs):
        self.records.append(kwargs)
        return kwargs


def build_gateway(
        provider: BaseModelProvider,
        log_service: MemoryLogService,
) -> ModelGateway:
    provider_router = ModelProviderRouter(
        providers={provider.provider_name: provider},
        default_llm_provider_name=provider.provider_name,
        default_embedding_provider_name=provider.provider_name,
    )
    return ModelGateway(
        provider_router=provider_router,
        log_service=log_service,
    )


@pytest.mark.anyio
async def test_chat_success_should_return_response_and_write_log():
    tenant_id = uuid.uuid4()
    log_service = MemoryLogService()
    gateway = build_gateway(FakeProvider(), log_service)

    result = await gateway.chat(
        ChatRequest(
            tenant_id=tenant_id,
            provider="fake",
            model="fake-chat-model",
            request_id="req_test",
            messages=[
                LLMMessage(role="user", content="你好"),
            ],
        )
    )

    assert result.content == "fake answer"
    assert len(log_service.records) == 1
    assert log_service.records[0]["tenant_id"] == tenant_id
    assert log_service.records[0]["provider"] == "fake"
    assert log_service.records[0]["model_type"] == "llm"
    assert log_service.records[0]["call_type"] == "chat"
    assert log_service.records[0]["status"] == "success"
    assert log_service.records[0]["input_tokens"] == 3
    assert log_service.records[0]["output_tokens"] == 2
    assert log_service.records[0]["metadata_json"]["retry_count"] == 0


@pytest.mark.anyio
async def test_embeddings_success_should_return_vectors_and_write_log():
    tenant_id = uuid.uuid4()
    log_service = MemoryLogService()
    gateway = build_gateway(FakeProvider(), log_service)

    result = await gateway.embeddings(
        EmbeddingRequest(
            tenant_id=tenant_id,
            provider="fake",
            model="fake-embedding-model",
            request_id="req_test",
            texts=["hello", "world"],
        )
    )

    assert len(result.embeddings) == 2
    assert result.embeddings[0] == [0.1, 0.2, 0.3]
    assert len(log_service.records) == 1
    assert log_service.records[0]["model_type"] == "embedding"
    assert log_service.records[0]["call_type"] == "embedding"
    assert log_service.records[0]["status"] == "success"
    assert log_service.records[0]["metadata_json"]["embedding_count"] == 2
    assert log_service.records[0]["metadata_json"]["retry_count"] == 0


@pytest.mark.anyio
async def test_chat_failure_should_write_failed_log_with_retry_count():
    tenant_id = uuid.uuid4()
    log_service = MemoryLogService()
    gateway = build_gateway(FailedProvider(), log_service)

    with pytest.raises(ModelGatewayException):
        await gateway.chat(
            ChatRequest(
                tenant_id=tenant_id,
                provider="fake",
                model="fake-chat-model",
                request_id="req_test",
                messages=[
                    LLMMessage(role="user", content="你好"),
                ],
            )
        )

    assert len(log_service.records) == 1
    assert log_service.records[0]["status"] == "failed"
    assert log_service.records[0]["error_code"] == "MODEL_PROVIDER_TIMEOUT"
    assert log_service.records[0]["metadata_json"]["retry_count"] == 2


@pytest.mark.anyio
async def test_stream_chat_should_yield_chunks_and_write_log():
    tenant_id = uuid.uuid4()
    log_service = MemoryLogService()
    gateway = build_gateway(FakeProvider(), log_service)

    chunks = []
    async for chunk in gateway.stream_chat(
        ChatRequest(
            tenant_id=tenant_id,
            provider="fake",
            model="fake-chat-model",
            request_id="req_test",
            messages=[
                LLMMessage(role="user", content="stream please"),
            ],
        )
    ):
        chunks.append(chunk)

    assert chunks == ["hello", " ", "world"]
    assert len(log_service.records) == 1
    assert log_service.records[0]["call_type"] == "stream_chat"
    assert log_service.records[0]["status"] == "success"
    assert log_service.records[0]["metadata_json"]["chunk_count"] == 3


@pytest.mark.anyio
async def test_gateway_should_use_default_chat_and_embedding_provider_separately():
    tenant_id = uuid.uuid4()
    log_service = MemoryLogService()

    mock_provider = FakeProvider()
    provider_router = ModelProviderRouter(
        providers={"fake": mock_provider},
        default_llm_provider_name="fake",
        default_embedding_provider_name="fake",
    )
    gateway = ModelGateway(
        provider_router=provider_router,
        log_service=log_service,
    )

    chat_result = await gateway.chat(
        ChatRequest(
            tenant_id=tenant_id,
            messages=[
                LLMMessage(role="user", content="hello"),
            ],
        )
    )

    embedding_result = await gateway.embeddings(
        EmbeddingRequest(
            tenant_id=tenant_id,
            texts=["hello"],
        )
    )

    assert chat_result.provider == "fake"
    assert embedding_result.provider == "fake"
    assert len(log_service.records) == 2


def test_truncate_text_should_limit_long_text():
    text = "a" * 600
    result = truncate_text(text, max_length=100)

    assert result is not None
    assert len(result) > 100
    assert result.endswith("...[truncated]")