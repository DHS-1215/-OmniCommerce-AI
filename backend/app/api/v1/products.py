# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/27 21:14
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.helpers import get_request_id, to_response_data
from app.core.response import ApiResponse, success_response
from app.db.session import get_db_session
from app.services.product_service import ProductService

router = APIRouter()

product_service = ProductService()


@router.get(
    "",
    response_model=ApiResponse,
    summary="查询商品列表",
)
async def list_products(
        request: Request,
        tenant_id: UUID = Query(..., description="租户 ID"),
        page: int = Query(default=1, ge=1, description="页码"),
        page_size: int = Query(default=20, ge=1, le=100, description="每页数量"),
        keyword: str | None = Query(default=None, description="搜索关键词"),
        brand: str | None = Query(default=None, description="品牌"),
        category: str | None = Query(default=None, description="类目"),
        db: AsyncSession = Depends(get_db_session),
) -> ApiResponse:
    """
    用户侧商品列表。

    默认只返回 active 商品。
    """

    data = await product_service.list_products(
        db,
        tenant_id=tenant_id,
        page=page,
        page_size=page_size,
        keyword=keyword,
        brand=brand,
        category=category,
    )
    return success_response(
        data=to_response_data(data),
        request_id=get_request_id(request),
    )


@router.get(
    "/admin/list",
    response_model=ApiResponse,
    summary="后台查询商品列表",
)
async def list_products_for_admin(
        request: Request,
        tenant_id: UUID = Query(..., description="租户 ID"),
        page: int = Query(default=1, ge=1, description="页码"),
        page_size: int = Query(default=20, ge=1, le=100, description="每页数量"),
        status: str | None = Query(default=None, description="商品状态"),
        keyword: str | None = Query(default=None, description="搜索关键词"),
        brand: str | None = Query(default=None, description="品牌"),
        category: str | None = Query(default=None, description="类目"),
        db: AsyncSession = Depends(get_db_session),
) -> ApiResponse:
    """
    后台商品列表。

    可按 status 查询 active / inactive / draft 商品。
    不传 status 时返回所有未软删除商品。
    """

    data = await product_service.list_products_for_admin(
        db,
        tenant_id=tenant_id,
        page=page,
        page_size=page_size,
        status_filter=status,
        keyword=keyword,
        brand=brand,
        category=category,
    )
    return success_response(
        data=to_response_data(data),
        request_id=get_request_id(request),
    )


@router.get(
    "/admin/{product_no}",
    response_model=ApiResponse,
    summary="后台查询商品详情",
)
async def get_product_detail_for_admin(
        request: Request,
        product_no: str = Path(..., description="商品业务编号"),
        tenant_id: UUID = Query(..., description="租户 ID"),
        db: AsyncSession = Depends(get_db_session),
) -> ApiResponse:
    """
    后台商品详情。

    可查询 inactive / draft 商品，并返回后台 SKU 信息。
    """

    data = await product_service.get_product_detail_for_admin(
        db,
        tenant_id=tenant_id,
        product_no=product_no,
    )
    return success_response(
        data=to_response_data(data),
        request_id=get_request_id(request),
    )


@router.get(
    "/skus/{sku_no}",
    response_model=ApiResponse,
    summary="查询 SKU 详情",
)
async def get_sku_detail(
        request: Request,
        sku_no: str = Path(..., description="SKU 业务编号"),
        tenant_id: UUID = Query(..., description="租户 ID"),
        db: AsyncSession = Depends(get_db_session),
) -> ApiResponse:
    """
    查询 SKU 详情。

    默认只返回 active SKU。
    """

    data = await product_service.get_sku_detail(
        db,
        tenant_id=tenant_id,
        sku_no=sku_no,
    )
    return success_response(
        data=to_response_data(data),
        request_id=get_request_id(request),
    )


@router.get(
    "/{product_no}/skus",
    response_model=ApiResponse,
    summary="查询商品 SKU 列表",
)
async def list_product_skus(
        request: Request,
        product_no: str = Path(..., description="商品业务编号"),
        tenant_id: UUID = Query(..., description="租户 ID"),
        db: AsyncSession = Depends(get_db_session),
) -> ApiResponse:
    """
    查询商品下的可售 SKU 列表。
    """

    data = await product_service.list_product_skus(
        db,
        tenant_id=tenant_id,
        product_no=product_no,
    )
    return success_response(
        data=to_response_data(data),
        request_id=get_request_id(request),
    )


@router.get(
    "/{product_no}/reviews",
    response_model=ApiResponse,
    summary="查询商品评价",
)
async def list_product_reviews(
        request: Request,
        product_no: str = Path(..., description="商品业务编号"),
        tenant_id: UUID = Query(..., description="租户 ID"),
        page: int = Query(default=1, ge=1, description="页码"),
        page_size: int = Query(default=20, ge=1, le=100, description="每页数量"),
        db: AsyncSession = Depends(get_db_session),
) -> ApiResponse:
    """
    查询商品可见评价。

    默认只返回 visible 评价。
    """

    data = await product_service.list_product_reviews(
        db,
        tenant_id=tenant_id,
        product_no=product_no,
        page=page,
        page_size=page_size,
    )
    return success_response(
        data=to_response_data(data),
        request_id=get_request_id(request),
    )


@router.get(
    "/{product_no}",
    response_model=ApiResponse,
    summary="查询商品详情",
)
async def get_product_detail(
        request: Request,
        product_no: str = Path(..., description="商品业务编号"),
        tenant_id: UUID = Query(..., description="租户 ID"),
        db: AsyncSession = Depends(get_db_session),
) -> ApiResponse:
    """
    用户侧商品详情。

    默认只返回 active 商品和 active SKU。
    """

    data = await product_service.get_product_detail(
        db,
        tenant_id=tenant_id,
        product_no=product_no,
    )
    return success_response(
        data=to_response_data(data),
        request_id=get_request_id(request),
    )
