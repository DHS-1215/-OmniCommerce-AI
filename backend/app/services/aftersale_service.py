# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/27 20:58
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
from app.models.ticket import AfterSaleTicket
from app.repositories.aftersale_repository import AfterSaleRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.user_repository import UserRepository
from app.schemas.aftersale import (
    AfterSaleCreateRequest,
    AfterSaleDetailResponse,
    AfterSaleListItemResponse,
)
from app.schemas.common import PageResponse


class AfterSaleService:
    """
    售后业务服务。

    窗口 3 只做基础售后单创建和查询：
    - 不做智能售后判断
    - 不做赔付策略
    - 不做模型调用
    - 不做 Agent 工具
    """

    def __init__(self) -> None:
        self.aftersale_repository = AfterSaleRepository()
        self.user_repository = UserRepository()
        self.order_repository = OrderRepository()

    async def list_after_sale_tickets(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            page: int,
            page_size: int,
            user_no: str | None = None,
            order_no: str | None = None,
            status_filter: str | None = None,
            after_sale_type: str | None = None,
    ) -> PageResponse[AfterSaleListItemResponse]:
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

        tickets, total = await self.aftersale_repository.list_tickets(
            db,
            tenant_id=tenant_id,
            page=page,
            page_size=page_size,
            user_id=user_id,
            order_id=order_id,
            status=status_filter,
            after_sale_type=after_sale_type,
        )

        return PageResponse[AfterSaleListItemResponse](
            items=[AfterSaleListItemResponse.model_validate(item) for item in tickets],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def get_after_sale_detail(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            ticket_no: str,
    ) -> AfterSaleDetailResponse:
        ticket = await self.aftersale_repository.get_by_ticket_no(
            db,
            tenant_id=tenant_id,
            ticket_no=ticket_no,
        )
        if ticket is None:
            raise BaseAppException(
                code="AFTER_SALE_TICKET_NOT_FOUND",
                message="售后单不存在",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        return AfterSaleDetailResponse.model_validate(ticket)

    async def create_after_sale_ticket(
            self,
            db: AsyncSession,
            *,
            request: AfterSaleCreateRequest,
    ) -> AfterSaleDetailResponse:
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

        order = await self.order_repository.get_by_order_no(
            db,
            tenant_id=request.tenant_id,
            order_no=request.order_no,
            include_items=True,
        )
        if order is None:
            raise BaseAppException(
                code="ORDER_NOT_FOUND",
                message="订单不存在",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        if order.user_id != user.id:
            raise BaseAppException(
                code="ORDER_USER_MISMATCH",
                message="订单不属于当前用户",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        if request.order_item_id is not None:
            order_item = await self.order_repository.get_item_by_id(
                db,
                tenant_id=request.tenant_id,
                order_item_id=request.order_item_id,
            )
            if order_item is None:
                raise BaseAppException(
                    code="ORDER_ITEM_NOT_FOUND",
                    message="订单明细不存在",
                    status_code=status.HTTP_404_NOT_FOUND,
                )

            if order_item.order_id != order.id:
                raise BaseAppException(
                    code="ORDER_ITEM_MISMATCH",
                    message="订单明细不属于当前订单",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

        ticket = AfterSaleTicket(
            tenant_id=request.tenant_id,
            ticket_no=self._generate_ticket_no(prefix="AS"),
            user_id=user.id,
            order_id=order.id,
            order_item_id=request.order_item_id,
            after_sale_type=request.after_sale_type,
            reason=request.reason,
            description=request.description,
            status="pending",
            refund_amount=request.refund_amount,
            currency=request.currency,
            evidence_json=request.evidence_json,
            audit_snapshot_json=None,
            metadata_json=request.metadata_json,
            submitted_at=datetime.now(UTC),
        )

        try:
            created_ticket = await self.aftersale_repository.create(
                db,
                ticket=ticket,
            )
            await db.commit()
        except Exception:
            await db.rollback()
            raise

        return AfterSaleDetailResponse.model_validate(created_ticket)

    @staticmethod
    def _generate_ticket_no(*, prefix: str) -> str:
        """
        生成业务单号。

        局部实现决策：
        - 当前窗口不引入全局发号器
        - 使用时间戳 + UUID 短码
        - 后续如需严格递增，可由总控确认后接入统一编号服务
        """

        now = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        suffix = uuid.uuid4().hex[:8].upper()
        return f"{prefix}{now}{suffix}"
