# -*- coding: utf-8 -*-
"""
创建时间    :2026/05/04 11:48
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content_review import ContentReview


class ContentReviewRepository:
    """内容审核记录数据访问层。

    只负责审核记录读写，不提交事务。
    """

    async def create(
            self,
            db: AsyncSession,
            review: ContentReview,
    ) -> ContentReview:
        db.add(review)
        await db.flush()
        await db.refresh(review)
        return review

    async def list_by_asset(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            content_asset_id: UUID,
    ) -> list[ContentReview]:
        stmt = (
            select(ContentReview)
            .where(ContentReview.tenant_id == tenant_id)
            .where(ContentReview.content_asset_id == content_asset_id)
            .order_by(ContentReview.created_at.desc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_latest_by_asset(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            content_asset_id: UUID,
            review_type: str | None = None,
    ) -> ContentReview | None:
        stmt = (
            select(ContentReview)
            .where(ContentReview.tenant_id == tenant_id)
            .where(ContentReview.content_asset_id == content_asset_id)
        )

        if review_type:
            stmt = stmt.where(ContentReview.review_type == review_type)

        stmt = stmt.order_by(ContentReview.created_at.desc()).limit(1)

        result = await db.execute(stmt)
        return result.scalar_one_or_none()
