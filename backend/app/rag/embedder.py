from __future__ import annotations

from typing import Sequence
from uuid import UUID

from app.llm.gateway import ModelGateway
from app.llm.schemas import EmbeddingRequest


class RagEmbedder:
    """
    RAG Embedding 封装。

    注意：
    这里不直接调用外部模型 API，必须通过窗口 4 的 ModelGateway。
    """

    def __init__(self, gateway: ModelGateway) -> None:
        self.gateway = gateway

    async def embed_texts(
        self,
        *,
        tenant_id: UUID,
        texts: Sequence[str],
        provider: str | None = None,
        model: str | None = None,
        request_id: str | None = None,
        user_id: UUID | None = None,
    ) -> list[list[float]]:
        if not texts:
            return []

        response = await self.gateway.embeddings(
            EmbeddingRequest(
                tenant_id=tenant_id,
                provider=provider,
                model=model,
                texts=list(texts),
                request_id=request_id,
                user_id=user_id,
            )
        )

        return response.embeddings

    async def embed_query(
        self,
        *,
        tenant_id: UUID,
        query: str,
        provider: str | None = None,
        model: str | None = None,
        request_id: str | None = None,
        user_id: UUID | None = None,
    ) -> list[float]:
        embeddings = await self.embed_texts(
            tenant_id=tenant_id,
            texts=[query],
            provider=provider,
            model=model,
            request_id=request_id,
            user_id=user_id,
        )

        return embeddings[0] if embeddings else []