# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/27 21:15
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.helpers import get_request_id, to_response_data
from app.core.response import ApiResponse, success_response
from app.db.session import get_db_session
from app.schemas.aftersale import AfterSaleCreateRequest
from app.services.aftersale_service import AfterSaleService

router = APIRouter()

aftersale_service = AfterSaleService()


@router.get(
    "",
    response_model=ApiResponse,
    summary="查询售后单列表",
)
async def list_after_sale_tickets(
        request: Request,
        tenant_id: UUID = Query(..., description="租户 ID"),
        page: int = Query(default=1, ge=1, description="页码"),
        page_size: int = Query(default=20, ge=1, le=100, description="每页数量"),
        user_no: str | None = Query(default=None, description="用户业务编号"),
        order_no: str | None = Query(default=None, description="订单业务编号"),
        status_filter: str | None = Query(
            default=None,
            alias="status",
            description="售后状态",
        ),
        after_sale_type: str | None = Query(default=None, description="售后类型"),
        db: AsyncSession = Depends(get_db_session),
) -> ApiResponse:
    """
    查询售后单列表。
    """

    data = await aftersale_service.list_after_sale_tickets(
        db,
        tenant_id=tenant_id,
        page=page,
        page_size=page_size,
        user_no=user_no,
        order_no=order_no,
        status_filter=status_filter,
        after_sale_type=after_sale_type,
    )
    return success_response(
        data=to_response_data(data),
        request_id=get_request_id(request),
    )


@router.post(
    "",
    response_model=ApiResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建售后单",
)
async def create_after_sale_ticket(
        request: Request,
        payload: AfterSaleCreateRequest,
        db: AsyncSession = Depends(get_db_session),
) -> ApiResponse:
    """
    创建售后单。

    窗口 3 只做基础售后申请创建：
    - 校验用户存在
    - 校验订单存在
    - 校验订单归属用户
    - 可选校验订单明细归属订单
    - 不做智能售后决策
    """

    data = await aftersale_service.create_after_sale_ticket(
        db,
        request=payload,
    )
    return success_response(
        data=to_response_data(data),
        message="created",
        request_id=get_request_id(request),
    )


@router.get(
    "/{ticket_no}",
    response_model=ApiResponse,
    summary="查询售后单详情",
)
async def get_after_sale_detail(
        request: Request,
        ticket_no: str = Path(..., description="售后单业务编号"),
        tenant_id: UUID = Query(..., description="租户 ID"),
        db: AsyncSession = Depends(get_db_session),
) -> ApiResponse:
    """
    查询售后单详情。
    """

    data = await aftersale_service.get_after_sale_detail(
        db,
        tenant_id=tenant_id,
        ticket_no=ticket_no,
    )
    return success_response(
        data=to_response_data(data),
        request_id=get_request_id(request),
    )
