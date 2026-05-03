# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/27 21:15
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
from app.services.order_service import OrderService

router = APIRouter()

order_service = OrderService()


@router.get(
    "",
    response_model=ApiResponse,
    summary="查询订单列表",
)
async def list_orders(
        request: Request,
        tenant_id: UUID = Query(..., description="租户 ID"),
        page: int = Query(default=1, ge=1, description="页码"),
        page_size: int = Query(default=20, ge=1, le=100, description="每页数量"),
        user_no: str | None = Query(default=None, description="用户业务编号"),
        order_status: str | None = Query(default=None, description="订单状态"),
        payment_status: str | None = Query(default=None, description="支付状态"),
        fulfillment_status: str | None = Query(default=None, description="履约状态"),
        db: AsyncSession = Depends(get_db_session),
) -> ApiResponse:
    """
    查询订单列表。

    可按用户、订单状态、支付状态、履约状态筛选。
    """

    data = await order_service.list_orders(
        db,
        tenant_id=tenant_id,
        page=page,
        page_size=page_size,
        user_no=user_no,
        order_status=order_status,
        payment_status=payment_status,
        fulfillment_status=fulfillment_status,
    )
    return success_response(
        data=to_response_data(data),
        request_id=get_request_id(request),
    )


@router.get(
    "/{order_no}",
    response_model=ApiResponse,
    summary="查询订单详情",
)
async def get_order_detail(
        request: Request,
        order_no: str = Path(..., description="订单业务编号"),
        tenant_id: UUID = Query(..., description="租户 ID"),
        db: AsyncSession = Depends(get_db_session),
) -> ApiResponse:
    """
    查询订单详情。

    返回订单主信息和订单明细。
    """

    data = await order_service.get_order_detail(
        db,
        tenant_id=tenant_id,
        order_no=order_no,
    )
    return success_response(
        data=to_response_data(data),
        request_id=get_request_id(request),
    )
