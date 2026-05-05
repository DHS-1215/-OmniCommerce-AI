# -*- coding: utf-8 -*-
"""
创建时间    :2026/05/04 11:47
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from __future__ import annotations

from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content_asset import ContentAsset


class ContentAssetRepository:
    """内容资产数据访问层。

    只负责数据库读写，不提交事务。
    事务边界由 service 层控制。
    """

    async def create(
            self,
            db: AsyncSession,
            asset: ContentAsset,
    ) -> ContentAsset:
        db.add(asset)
        await db.flush()
        await db.refresh(asset)
        return asset

    async def get_by_id(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            asset_id: UUID,
    ) -> ContentAsset | None:
        stmt = (
            select(ContentAsset)
            .where(ContentAsset.tenant_id == tenant_id)
            .where(ContentAsset.id == asset_id)
            .where(ContentAsset.deleted_at.is_(None))
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_versions(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            asset_group_id: UUID,
    ) -> list[ContentAsset]:
        stmt = (
            select(ContentAsset)
            .where(ContentAsset.tenant_id == tenant_id)
            .where(ContentAsset.asset_group_id == asset_group_id)
            .where(ContentAsset.deleted_at.is_(None))
            .order_by(ContentAsset.version.desc(), ContentAsset.created_at.desc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_latest_version(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            asset_group_id: UUID,
    ) -> ContentAsset | None:
        stmt = (
            select(ContentAsset)
            .where(ContentAsset.tenant_id == tenant_id)
            .where(ContentAsset.asset_group_id == asset_group_id)
            .where(ContentAsset.deleted_at.is_(None))
            .order_by(ContentAsset.version.desc())
            .limit(1)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_next_version(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            asset_group_id: UUID,
    ) -> int:
        stmt = (
            select(func.max(ContentAsset.version))
            .where(ContentAsset.tenant_id == tenant_id)
            .where(ContentAsset.asset_group_id == asset_group_id)
            .where(ContentAsset.deleted_at.is_(None))
        )
        result = await db.execute(stmt)
        max_version = result.scalar_one_or_none()
        return int(max_version or 0) + 1

    async def list_by_biz(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            biz_type: str,
            biz_id: str | None,
            content_type: str | None = None,
    ) -> list[ContentAsset]:
        stmt: Select[tuple[ContentAsset]] = (
            select(ContentAsset)
            .where(ContentAsset.tenant_id == tenant_id)
            .where(ContentAsset.biz_type == biz_type)
            .where(ContentAsset.deleted_at.is_(None))
        )

        if biz_id is None:
            stmt = stmt.where(ContentAsset.biz_id.is_(None))
        else:
            stmt = stmt.where(ContentAsset.biz_id == biz_id)

        if content_type:
            stmt = stmt.where(ContentAsset.content_type == content_type)

        stmt = stmt.order_by(ContentAsset.created_at.desc())

        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def update_review_state(
            self,
            db: AsyncSession,
            *,
            asset: ContentAsset,
            status: str,
            review_status: str,
            approved_by: str | None = None,
            approved_at=None,
    ) -> ContentAsset:
        asset.status = status
        asset.review_status = review_status

        if approved_by is not None:
            asset.approved_by = approved_by

        if approved_at is not None:
            asset.approved_at = approved_at

        await db.flush()
        await db.refresh(asset)
        return asset
