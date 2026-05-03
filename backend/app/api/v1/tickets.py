# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/27 21:20
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
from app.schemas.ticket import CustomerServiceTicketCreateRequest
from app.services.ticket_service import CustomerServiceTicketService

router = APIRouter()

ticket_service = CustomerServiceTicketService()


@router.get(
    "",
    response_model=ApiResponse,
    summary="查询客服工单列表",
)
async def list_customer_service_tickets(
        request: Request,
        tenant_id: UUID = Query(..., description="租户 ID"),
        page: int = Query(default=1, ge=1, description="页码"),
        page_size: int = Query(default=20, ge=1, le=100, description="每页数量"),
        user_no: str | None = Query(default=None, description="用户业务编号"),
        order_no: str | None = Query(default=None, description="订单业务编号"),
        status_filter: str | None = Query(
            default=None,
            alias="status",
            description="工单状态",
        ),
        category: str | None = Query(default=None, description="工单分类"),
        priority: str | None = Query(default=None, description="优先级"),
        db: AsyncSession = Depends(get_db_session),
) -> ApiResponse:
    """
    查询客服工单列表。
    """

    data = await ticket_service.list_tickets(
        db,
        tenant_id=tenant_id,
        page=page,
        page_size=page_size,
        user_no=user_no,
        order_no=order_no,
        status_filter=status_filter,
        category=category,
        priority=priority,
    )
    return success_response(
        data=to_response_data(data),
        request_id=get_request_id(request),
    )


@router.post(
    "",
    response_model=ApiResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建客服工单",
)
async def create_customer_service_ticket(
        request: Request,
        payload: CustomerServiceTicketCreateRequest,
        db: AsyncSession = Depends(get_db_session),
) -> ApiResponse:
    """
    创建客服工单。

    窗口 3 只做基础工单创建，不做 Agent 转人工策略。
    后续窗口 7 可以复用 service 层创建工单。
    """

    data = await ticket_service.create_ticket(
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
    summary="查询客服工单详情",
)
async def get_customer_service_ticket_detail(
        request: Request,
        ticket_no: str = Path(..., description="客服工单业务编号"),
        tenant_id: UUID = Query(..., description="租户 ID"),
        db: AsyncSession = Depends(get_db_session),
) -> ApiResponse:
    """
    查询客服工单详情。
    """

    data = await ticket_service.get_ticket_detail(
        db,
        tenant_id=tenant_id,
        ticket_no=ticket_no,
    )
    return success_response(
        data=to_response_data(data),
        request_id=get_request_id(request),
    )
