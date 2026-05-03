# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/27 20:59
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
import uuid
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.core.exceptions import BaseAppException
from app.models.ticket import CustomerServiceTicket
from app.repositories.order_repository import OrderRepository
from app.repositories.ticket_repository import CustomerServiceTicketRepository
from app.repositories.user_repository import UserRepository
from app.schemas.common import PageResponse
from app.schemas.ticket import (
    CustomerServiceTicketCreateRequest,
    CustomerServiceTicketDetailResponse,
    CustomerServiceTicketListItemResponse,
)


class CustomerServiceTicketService:
    """
    客服工单业务服务。

    窗口 3 只做基础工单创建和查询。
    后续窗口 7 的客服 Agent 可以复用本 service 创建转人工工单。
    """

    def __init__(self) -> None:
        self.ticket_repository = CustomerServiceTicketRepository()
        self.user_repository = UserRepository()
        self.order_repository = OrderRepository()

    async def list_tickets(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            page: int,
            page_size: int,
            user_no: str | None = None,
            order_no: str | None = None,
            status_filter: str | None = None,
            category: str | None = None,
            priority: str | None = None,
    ) -> PageResponse[CustomerServiceTicketListItemResponse]:
        user_id = None
        order_id = None

        if user_no:
            user = await self.user_repository.get_by_user_no(
                db,
                tenant_id=tenant_id,
                user_no=user_no,
            )
            if user is None:
                raise BaseAppException(
                    code="USER_NOT_FOUND",
                    message="用户不存在",
                    status_code=status.HTTP_404_NOT_FOUND,
                )
            user_id = user.id

        if order_no:
            order = await self.order_repository.get_by_order_no(
                db,
                tenant_id=tenant_id,
                order_no=order_no,
            )
            if order is None:
                raise BaseAppException(
                    code="ORDER_NOT_FOUND",
                    message="订单不存在",
                    status_code=status.HTTP_404_NOT_FOUND,
                )
            order_id = order.id

        tickets, total = await self.ticket_repository.list_tickets(
            db,
            tenant_id=tenant_id,
            page=page,
            page_size=page_size,
            user_id=user_id,
            order_id=order_id,
            status=status_filter,
            category=category,
            priority=priority,
        )

        return PageResponse[CustomerServiceTicketListItemResponse](
            items=[
                CustomerServiceTicketListItemResponse.model_validate(item)
                for item in tickets
            ],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def get_ticket_detail(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            ticket_no: str,
    ) -> CustomerServiceTicketDetailResponse:
        ticket = await self.ticket_repository.get_by_ticket_no(
            db,
            tenant_id=tenant_id,
            ticket_no=ticket_no,
        )
        if ticket is None:
            raise BaseAppException(
                code="CUSTOMER_SERVICE_TICKET_NOT_FOUND",
                message="客服工单不存在",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        return CustomerServiceTicketDetailResponse.model_validate(ticket)

    async def create_ticket(
            self,
            db: AsyncSession,
            *,
            request: CustomerServiceTicketCreateRequest,
    ) -> CustomerServiceTicketDetailResponse:
        user_id = None
        order_id = None

        if request.user_no:
            user = await self.user_repository.get_by_user_no(
                db,
                tenant_id=request.tenant_id,
                user_no=request.user_no,
            )
            if user is None:
                raise BaseAppException(
                    code="USER_NOT_FOUND",
                    message="用户不存在",
                    status_code=status.HTTP_404_NOT_FOUND,
                )
            user_id = user.id

        if request.order_no:
            order = await self.order_repository.get_by_order_no(
                db,
                tenant_id=request.tenant_id,
                order_no=request.order_no,
            )
            if order is None:
                raise BaseAppException(
                    code="ORDER_NOT_FOUND",
                    message="订单不存在",
                    status_code=status.HTTP_404_NOT_FOUND,
                )

            if user_id is not None and order.user_id != user_id:
                raise BaseAppException(
                    code="ORDER_USER_MISMATCH",
                    message="订单不属于当前用户",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            order_id = order.id

        ticket = CustomerServiceTicket(
            tenant_id=request.tenant_id,
            ticket_no=self._generate_ticket_no(prefix="CS"),
            user_id=user_id,
            order_id=order_id,
            source=request.source,
            channel=request.channel,
            category=request.category,
            priority=request.priority,
            status="open",
            title=request.title,
            content=request.content,
            assigned_operator_id=request.assigned_operator_id,
            resolution=None,
            related_agent_task_id=None,
            metadata_json=request.metadata_json,
            opened_at=datetime.now(UTC),
        )

        try:
            created_ticket = await self.ticket_repository.create(
                db,
                ticket=ticket,
            )
            await db.commit()
        except Exception:
            await db.rollback()
            raise

        return CustomerServiceTicketDetailResponse.model_validate(created_ticket)

    @staticmethod
    def _generate_ticket_no(*, prefix: str) -> str:
        """
        生成客服工单业务编号。
        """

        now = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        suffix = uuid.uuid4().hex[:8].upper()
        return f"{prefix}{now}{suffix}"
