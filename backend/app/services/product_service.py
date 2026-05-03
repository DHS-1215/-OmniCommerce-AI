# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/27 20:56
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.core.exceptions import BaseAppException
from app.repositories.product_repository import ProductRepository
from app.schemas.common import PageResponse
from app.schemas.product import (
    ProductAdminItemResponse,
    ProductDetailResponse,
    ProductListItemResponse,
    ProductReviewResponse,
    ProductSkuAdminResponse,
    ProductSkuResponse,
)


class ProductService:
    """
    商品业务服务。

    注意：
    - 普通用户侧接口默认只返回 active 商品 / active SKU / visible 评价
    - 后台管理接口允许查询 inactive / draft 商品
    """

    def __init__(self) -> None:
        self.product_repository = ProductRepository()

    async def list_products(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            page: int,
            page_size: int,
            keyword: str | None = None,
            brand: str | None = None,
            category: str | None = None,
    ) -> PageResponse[ProductListItemResponse]:
        products, total = await self.product_repository.list_products(
            db,
            tenant_id=tenant_id,
            page=page,
            page_size=page_size,
            status="active",
            keyword=keyword,
            brand=brand,
            category=category,
        )

        return PageResponse[ProductListItemResponse](
            items=[ProductListItemResponse.model_validate(item) for item in products],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def list_products_for_admin(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            page: int,
            page_size: int,
            status_filter: str | None = None,
            keyword: str | None = None,
            brand: str | None = None,
            category: str | None = None,
    ) -> PageResponse[ProductListItemResponse]:
        products, total = await self.product_repository.list_products(
            db,
            tenant_id=tenant_id,
            page=page,
            page_size=page_size,
            status=status_filter,
            keyword=keyword,
            brand=brand,
            category=category,
        )

        return PageResponse[ProductListItemResponse](
            items=[ProductListItemResponse.model_validate(item) for item in products],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def get_product_detail(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            product_no: str,
    ) -> ProductDetailResponse:
        product = await self.product_repository.get_by_product_no(
            db,
            tenant_id=tenant_id,
            product_no=product_no,
            status="active",
        )
        if product is None:
            raise BaseAppException(
                code="PRODUCT_NOT_FOUND",
                message="商品不存在或已下架",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        skus = await self.product_repository.list_skus_by_product_id(
            db,
            tenant_id=tenant_id,
            product_id=product.id,
            status="active",
        )

        data = ProductDetailResponse.model_validate(product)
        data.skus = [ProductSkuResponse.model_validate(sku) for sku in skus]
        return data

    async def get_product_detail_for_admin(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            product_no: str,
    ) -> ProductAdminItemResponse:
        product = await self.product_repository.get_by_product_no(
            db,
            tenant_id=tenant_id,
            product_no=product_no,
            status=None,
        )
        if product is None:
            raise BaseAppException(
                code="PRODUCT_NOT_FOUND",
                message="商品不存在",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        skus = await self.product_repository.list_skus_by_product_id(
            db,
            tenant_id=tenant_id,
            product_id=product.id,
            status=None,
        )

        data = ProductAdminItemResponse.model_validate(product)
        data.skus = [ProductSkuAdminResponse.model_validate(sku) for sku in skus]
        return data

    async def list_product_skus(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            product_no: str,
    ) -> list[ProductSkuResponse]:
        product = await self.product_repository.get_by_product_no(
            db,
            tenant_id=tenant_id,
            product_no=product_no,
            status="active",
        )
        if product is None:
            raise BaseAppException(
                code="PRODUCT_NOT_FOUND",
                message="商品不存在或已下架",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        skus = await self.product_repository.list_skus_by_product_id(
            db,
            tenant_id=tenant_id,
            product_id=product.id,
            status="active",
        )
        return [ProductSkuResponse.model_validate(sku) for sku in skus]

    async def get_sku_detail(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            sku_no: str,
    ) -> ProductSkuResponse:
        sku = await self.product_repository.get_sku_by_sku_no(
            db,
            tenant_id=tenant_id,
            sku_no=sku_no,
            status="active",
        )
        if sku is None:
            raise BaseAppException(
                code="SKU_NOT_FOUND",
                message="SKU 不存在或不可售",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        return ProductSkuResponse.model_validate(sku)

    async def list_product_reviews(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            product_no: str,
            page: int,
            page_size: int,
    ) -> PageResponse[ProductReviewResponse]:
        product = await self.product_repository.get_by_product_no(
            db,
            tenant_id=tenant_id,
            product_no=product_no,
            status="active",
        )
        if product is None:
            raise BaseAppException(
                code="PRODUCT_NOT_FOUND",
                message="商品不存在或已下架",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        reviews, total = await self.product_repository.list_reviews_by_product_id(
            db,
            tenant_id=tenant_id,
            product_id=product.id,
            page=page,
            page_size=page_size,
            status="visible",
        )

        return PageResponse[ProductReviewResponse](
            items=[ProductReviewResponse.model_validate(item) for item in reviews],
            total=total,
            page=page,
            page_size=page_size,
        )
