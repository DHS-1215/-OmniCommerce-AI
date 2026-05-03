# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/27 20:57
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.core.exceptions import BaseAppException
from app.repositories.order_repository import OrderRepository
from app.repositories.user_repository import UserRepository
from app.schemas.common import PageResponse
from app.schemas.order import (
    OrderDetailResponse,
    OrderItemResponse,
    OrderListItemResponse,
)


class OrderService:
    """
    订单业务服务。
    """

    def __init__(self) -> None:
        self.order_repository = OrderRepository()
        self.user_repository = UserRepository()

    async def list_orders(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            page: int,
            page_size: int,
            user_no: str | None = None,
            order_status: str | None = None,
            payment_status: str | None = None,
            fulfillment_status: str | None = None,
    ) -> PageResponse[OrderListItemResponse]:
        user_id = None

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

        orders, total = await self.order_repository.list_orders(
            db,
            tenant_id=tenant_id,
            page=page,
            page_size=page_size,
            user_id=user_id,
            order_status=order_status,
            payment_status=payment_status,
            fulfillment_status=fulfillment_status,
        )

        return PageResponse[OrderListItemResponse](
            items=[OrderListItemResponse.model_validate(item) for item in orders],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def get_order_detail(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            order_no: str,
    ) -> OrderDetailResponse:
        order = await self.order_repository.get_by_order_no(
            db,
            tenant_id=tenant_id,
            order_no=order_no,
            include_items=True,
        )
        if order is None:
            raise BaseAppException(
                code="ORDER_NOT_FOUND",
                message="订单不存在",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        data = OrderDetailResponse.model_validate(order)
        data.items = [
            OrderItemResponse.model_validate(item)
            for item in order.items
            if item.deleted_at is None
        ]
        return data
