# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/05/01 22:25
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from app.rag.embedder import RagEmbedder
from app.rag.keyword_store import KeywordSearchHit, KeywordStore
from app.rag.vector_store import QdrantVectorStore, VectorSearchHit


@dataclass(slots=True)
class RetrievalHit:
    """
    混合检索命中结果。
    """

    chunk_id: UUID
    document_id: UUID
    score: float
    vector_score: float = 0.0
    keyword_score: float = 0.0
    payload: dict[str, Any] = field(default_factory=dict)


class HybridRetriever:
    """
    混合检索器。

    当前策略：
    - 向量检索
    - 关键词检索
    - 按 chunk_id 融合分数

    后续可以替换：
    - KeywordStore -> OpenSearchKeywordStore
    - NoopReranker -> 真实 Reranker
    """

    def __init__(
        self,
        *,
        embedder: RagEmbedder,
        vector_store: QdrantVectorStore,
        keyword_store: KeywordStore,
        vector_weight: float = 0.65,
        keyword_weight: float = 0.35,
    ) -> None:
        self.embedder = embedder
        self.vector_store = vector_store
        self.keyword_store = keyword_store
        self.vector_weight = vector_weight
        self.keyword_weight = keyword_weight

    async def retrieve(
        self,
        *,
        tenant_id: UUID,
        query: str,
        top_k: int,
        request_id: str | None = None,
        user_id: UUID | None = None,
    ) -> list[RetrievalHit]:
        query_vector = await self.embedder.embed_query(
            tenant_id=tenant_id,
            query=query,
            request_id=request_id,
            user_id=user_id,
        )

        vector_hits = self.vector_store.search(
            tenant_id=tenant_id,
            query_vector=query_vector,
            top_k=top_k,
        )

        keyword_hits = await self.keyword_store.search(
            tenant_id=tenant_id,
            query=query,
            top_k=top_k,
        )

        merged = self._merge_hits(
            vector_hits=vector_hits,
            keyword_hits=keyword_hits,
        )

        merged.sort(key=lambda item: item.score, reverse=True)

        return merged[:top_k]

    def _merge_hits(
        self,
        *,
        vector_hits: list[VectorSearchHit],
        keyword_hits: list[KeywordSearchHit],
    ) -> list[RetrievalHit]:
        merged: dict[UUID, RetrievalHit] = {}

        normalized_vector_scores = self._normalize_scores(
            {hit.chunk_id: hit.score for hit in vector_hits}
        )
        normalized_keyword_scores = self._normalize_scores(
            {hit.chunk_id: hit.score for hit in keyword_hits}
        )

        for hit in vector_hits:
            vector_score = normalized_vector_scores.get(hit.chunk_id, 0.0)
            payload = dict(hit.payload)

            merged[hit.chunk_id] = RetrievalHit(
                chunk_id=hit.chunk_id,
                document_id=hit.document_id,
                score=vector_score * self.vector_weight,
                vector_score=vector_score,
                keyword_score=0.0,
                payload=payload,
            )

        for hit in keyword_hits:
            keyword_score = normalized_keyword_scores.get(hit.chunk_id, 0.0)

            if hit.chunk_id not in merged:
                merged[hit.chunk_id] = RetrievalHit(
                    chunk_id=hit.chunk_id,
                    document_id=hit.document_id,
                    score=keyword_score * self.keyword_weight,
                    vector_score=0.0,
                    keyword_score=keyword_score,
                    payload=dict(hit.payload),
                )
                continue

            existing = merged[hit.chunk_id]
            existing.keyword_score = keyword_score
            existing.score = (
                existing.vector_score * self.vector_weight
                + existing.keyword_score * self.keyword_weight
            )

            existing.payload = {
                **hit.payload,
                **existing.payload,
            }

        return list(merged.values())

    @staticmethod
    def _normalize_scores(scores: dict[UUID, float]) -> dict[UUID, float]:
        if not scores:
            return {}

        max_score = max(scores.values())

        if max_score <= 0:
            return {key: 0.0 for key in scores}

        return {
            key: value / max_score
            for key, value in scores.items()
        }