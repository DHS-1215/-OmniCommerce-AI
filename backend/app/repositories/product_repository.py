# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/27 20:48
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.product import Product, ProductReview, ProductSku


class ProductRepository:
    """
    商品、SKU、评价数据访问层。
    """

    async def list_products(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            page: int,
            page_size: int,
            status: str | None = "active",
            keyword: str | None = None,
            brand: str | None = None,
            category: str | None = None,
    ) -> tuple[list[Product], int]:
        conditions = [
            Product.tenant_id == tenant_id,
            Product.deleted_at.is_(None),
        ]

        if status:
            conditions.append(Product.status == status)

        if brand:
            conditions.append(Product.brand == brand)

        if category:
            conditions.append(Product.category == category)

        if keyword:
            like_keyword = f"%{keyword}%"
            conditions.append(
                or_(
                    Product.product_no.ilike(like_keyword),
                    Product.title.ilike(like_keyword),
                    Product.subtitle.ilike(like_keyword),
                    Product.brand.ilike(like_keyword),
                    Product.category.ilike(like_keyword),
                )
            )

        count_stmt = select(func.count()).select_from(Product).where(*conditions)
        total = await db.scalar(count_stmt)
        total = int(total or 0)

        stmt = (
            select(Product)
            .where(*conditions)
            .order_by(Product.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all()), total

    async def get_by_product_no(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            product_no: str,
            status: str | None = "active",
            include_skus: bool = False,
    ) -> Product | None:
        conditions = [
            Product.tenant_id == tenant_id,
            Product.product_no == product_no,
            Product.deleted_at.is_(None),
        ]

        if status:
            conditions.append(Product.status == status)

        stmt = select(Product).where(*conditions)

        if include_skus:
            stmt = stmt.options(selectinload(Product.skus))

        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            product_id: UUID,
            status: str | None = "active",
    ) -> Product | None:
        conditions = [
            Product.tenant_id == tenant_id,
            Product.id == product_id,
            Product.deleted_at.is_(None),
        ]

        if status:
            conditions.append(Product.status == status)

        stmt = select(Product).where(*conditions)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_skus_by_product_id(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            product_id: UUID,
            status: str | None = "active",
    ) -> list[ProductSku]:
        conditions = [
            ProductSku.tenant_id == tenant_id,
            ProductSku.product_id == product_id,
            ProductSku.deleted_at.is_(None),
        ]

        if status:
            conditions.append(ProductSku.status == status)

        stmt = (
            select(ProductSku)
            .where(*conditions)
            .order_by(ProductSku.created_at.asc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_sku_by_sku_no(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            sku_no: str,
            status: str | None = "active",
    ) -> ProductSku | None:
        conditions = [
            ProductSku.tenant_id == tenant_id,
            ProductSku.sku_no == sku_no,
            ProductSku.deleted_at.is_(None),
        ]

        if status:
            conditions.append(ProductSku.status == status)

        stmt = select(ProductSku).where(*conditions)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_reviews_by_product_id(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            product_id: UUID,
            page: int,
            page_size: int,
            status: str | None = "visible",
    ) -> tuple[list[ProductReview], int]:
        conditions = [
            ProductReview.tenant_id == tenant_id,
            ProductReview.product_id == product_id,
            ProductReview.deleted_at.is_(None),
        ]

        if status:
            conditions.append(ProductReview.status == status)

        count_stmt = select(func.count()).select_from(ProductReview).where(*conditions)
        total = await db.scalar(count_stmt)
        total = int(total or 0)

        stmt = (
            select(ProductReview)
            .where(*conditions)
            .order_by(ProductReview.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all()), total
