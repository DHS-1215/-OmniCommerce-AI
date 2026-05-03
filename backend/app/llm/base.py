# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/28 17:57
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from app.llm.schemas import ChatRequest, ChatResponse, EmbeddingRequest, EmbeddingResponse


class BaseModelProvider(ABC):
    """
    模型 Provider 抽象基类。

    后续接入 OpenAI-compatible、Azure OpenAI、私有模型服务等 Provider，
    都必须实现该接口，不能让业务模块直接调用外部模型 API。
    """

    provider_name: str

    @abstractmethod
    async def chat(self, request: ChatRequest) -> ChatResponse:
        """
        普通 LLM 文本调用。
        """
        raise NotImplementedError

    @abstractmethod
    async def embeddings(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """
        Embedding 调用。
        """
        raise NotImplementedError

    @abstractmethod
    async def stream_chat(self, request: ChatRequest) -> AsyncIterator[str]:
        """
        流式 LLM 输出。

        返回增量文本片段，不直接绑定 FastAPI StreamingResponse，
        这样 Agent / RAG / API 层都可以复用。
        """
        raise NotImplementedError
