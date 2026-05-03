# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/05/01 22:43
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from typing import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import KnowledgeChunk, KnowledgeDocument


class KnowledgeRepository:
    """
    知识库数据库访问层。

    只负责 PostgreSQL 数据访问，不负责解析、切片、Embedding、Qdrant。
    """

    def __init__(self, db_session: AsyncSession) -> None:
        self.db_session = db_session

    async def create_document(
        self,
        document: KnowledgeDocument,
    ) -> KnowledgeDocument:
        self.db_session.add(document)
        await self.db_session.flush()
        await self.db_session.refresh(document)
        return document

    async def update_document_status(
        self,
        *,
        document_id: UUID,
        status: str | None = None,
        parser_status: str | None = None,
    ) -> KnowledgeDocument | None:
        document = await self.get_document_by_id(document_id=document_id)

        if document is None:
            return None

        if status is not None:
            document.status = status

        if parser_status is not None:
            document.parser_status = parser_status

        await self.db_session.flush()
        await self.db_session.refresh(document)

        return document

    async def get_document_by_id(
        self,
        *,
        document_id: UUID,
    ) -> KnowledgeDocument | None:
        stmt = (
            select(KnowledgeDocument)
            .where(KnowledgeDocument.id == document_id)
            .where(KnowledgeDocument.deleted_at.is_(None))
        )

        result = await self.db_session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_document_by_no(
        self,
        *,
        tenant_id: UUID,
        document_no: str,
    ) -> KnowledgeDocument | None:
        stmt = (
            select(KnowledgeDocument)
            .where(KnowledgeDocument.tenant_id == tenant_id)
            .where(KnowledgeDocument.document_no == document_no)
            .where(KnowledgeDocument.deleted_at.is_(None))
        )

        result = await self.db_session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_documents(
        self,
        *,
        tenant_id: UUID,
        page: int,
        page_size: int,
        status: str | None = None,
        keyword: str | None = None,
    ) -> tuple[list[KnowledgeDocument], int]:
        stmt = (
            select(KnowledgeDocument)
            .where(KnowledgeDocument.tenant_id == tenant_id)
            .where(KnowledgeDocument.deleted_at.is_(None))
        )

        count_stmt = (
            select(func.count(KnowledgeDocument.id))
            .where(KnowledgeDocument.tenant_id == tenant_id)
            .where(KnowledgeDocument.deleted_at.is_(None))
        )

        if status:
            stmt = stmt.where(KnowledgeDocument.status == status)
            count_stmt = count_stmt.where(KnowledgeDocument.status == status)

        if keyword:
            like_keyword = f"%{keyword}%"
            stmt = stmt.where(KnowledgeDocument.title.ilike(like_keyword))
            count_stmt = count_stmt.where(KnowledgeDocument.title.ilike(like_keyword))

        stmt = (
            stmt.order_by(KnowledgeDocument.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        rows_result = await self.db_session.execute(stmt)
        count_result = await self.db_session.execute(count_stmt)

        return list(rows_result.scalars().all()), int(count_result.scalar_one())

    async def create_chunks(
        self,
        chunks: Sequence[KnowledgeChunk],
    ) -> list[KnowledgeChunk]:
        if not chunks:
            return []

        self.db_session.add_all(list(chunks))
        await self.db_session.flush()

        for chunk in chunks:
            await self.db_session.refresh(chunk)

        return list(chunks)

    async def list_chunks_by_document_id(
        self,
        *,
        document_id: UUID,
    ) -> list[KnowledgeChunk]:
        stmt = (
            select(KnowledgeChunk)
            .where(KnowledgeChunk.document_id == document_id)
            .where(KnowledgeChunk.deleted_at.is_(None))
            .order_by(KnowledgeChunk.chunk_no.asc())
        )

        result = await self.db_session.execute(stmt)
        return list(result.scalars().all())

    async def get_chunk_by_id(
        self,
        *,
        chunk_id: UUID,
    ) -> KnowledgeChunk | None:
        stmt = (
            select(KnowledgeChunk)
            .where(KnowledgeChunk.id == chunk_id)
            .where(KnowledgeChunk.deleted_at.is_(None))
        )

        result = await self.db_session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_chunks_with_documents_by_ids(
        self,
        *,
        tenant_id: UUID,
        chunk_ids: Sequence[UUID],
    ) -> list[tuple[KnowledgeChunk, KnowledgeDocument]]:
        if not chunk_ids:
            return []

        stmt = (
            select(KnowledgeChunk, KnowledgeDocument)
            .join(KnowledgeDocument, KnowledgeDocument.id == KnowledgeChunk.document_id)
            .where(KnowledgeChunk.tenant_id == tenant_id)
            .where(KnowledgeDocument.tenant_id == tenant_id)
            .where(KnowledgeChunk.id.in_(chunk_ids))
            .where(KnowledgeChunk.deleted_at.is_(None))
            .where(KnowledgeDocument.deleted_at.is_(None))
        )

        result = await self.db_session.execute(stmt)
        return list(result.all())