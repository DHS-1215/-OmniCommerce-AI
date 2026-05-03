# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/28 17:58
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from collections.abc import AsyncIterator

from app.llm.base import BaseModelProvider
from app.llm.schemas import (
    ChatRequest,
    ChatResponse,
    EmbeddingRequest,
    EmbeddingResponse,
    TokenUsage,
)


class MockProvider(BaseModelProvider):
    """
    正式 Mock Provider。

    用途：
    - 本地开发无 API Key 时可运行；
    - 自动化测试不依赖真实模型；
    - 后续 Agent / RAG 测试可复用稳定输出。
    """

    provider_name = "mock"

    async def chat(self, request: ChatRequest) -> ChatResponse:
        user_messages = [
            message.content for message in request.messages if message.role == "user"
        ]
        last_user_message = user_messages[-1] if user_messages else ""

        return ChatResponse(
            provider=self.provider_name,
            model_name=request.model or "mock-chat-model",
            content=f"[mock] {last_user_message}",
            usage=TokenUsage(
                input_tokens=10,
                output_tokens=5,
                total_tokens=15,
            ),
            latency_ms=1,
            raw_response_id="mock_chat_response",
        )

    async def embeddings(self, request: EmbeddingRequest) -> EmbeddingResponse:
        embeddings = []

        for index, text in enumerate(request.texts):
            base = float((len(text) + index) % 10) / 10
            embeddings.append([base, base + 0.1, base + 0.2])

        return EmbeddingResponse(
            provider=self.provider_name,
            model_name=request.model or "mock-embedding-model",
            embeddings=embeddings,
            usage=TokenUsage(
                input_tokens=len(request.texts) * 5,
                output_tokens=0,
                total_tokens=len(request.texts) * 5,
            ),
            latency_ms=1,
            raw_response_id="mock_embedding_response",
        )

    async def stream_chat(self, request: ChatRequest) -> AsyncIterator[str]:
        yield "[mock]"
        yield " stream"
        yield " response"