# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/05/02 10:54
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from typing import Any, Sequence
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rag import RagRetrievalLog


class RagRetrievalLogRepository:
    """
    RAG 检索日志 Repository。

    只负责 rag_retrieval_log 表写入，不参与检索业务逻辑。
    """

    def __init__(self, db_session: AsyncSession) -> None:
        self.db_session = db_session

    async def create_log(
            self,
            *,
            tenant_id: UUID,
            query: str,
            retrieval_mode: str,
            top_k: int,
            result_count: int,
            retrieved_chunk_ids: Sequence[str],
            retrieved_document_ids: Sequence[str],
            vector_score: float,
            keyword_score: float,
            final_score: float,
            scores_json: list[dict[str, Any]],
            latency_ms: int,
            request_id: str | None = None,
            user_id: UUID | None = None,
            metadata_json: dict[str, Any] | None = None,
    ) -> RagRetrievalLog:
        log = RagRetrievalLog(
            tenant_id=tenant_id,
            user_id=user_id,
            request_id=request_id,
            query=query,
            retrieval_mode=retrieval_mode,
            top_k=top_k,
            result_count=result_count,
            retrieved_chunk_ids=list(retrieved_chunk_ids),
            retrieved_document_ids=list(retrieved_document_ids),
            vector_score=vector_score,
            keyword_score=keyword_score,
            final_score=final_score,
            scores_json=scores_json,
            latency_ms=latency_ms,
            metadata_json=metadata_json or {},
        )

        self.db_session.add(log)
        await self.db_session.flush()
        await self.db_session.refresh(log)

        return log
