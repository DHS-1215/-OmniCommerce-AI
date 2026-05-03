# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/27 20:48
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.order import OrderInfo, OrderItem


class OrderRepository:
    """
    订单数据访问层。
    """

    async def list_orders(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            page: int,
            page_size: int,
            user_id: UUID | None = None,
            order_status: str | None = None,
            payment_status: str | None = None,
            fulfillment_status: str | None = None,
    ) -> tuple[list[OrderInfo], int]:
        conditions = [
            OrderInfo.tenant_id == tenant_id,
            OrderInfo.deleted_at.is_(None),
        ]

        if user_id:
            conditions.append(OrderInfo.user_id == user_id)

        if order_status:
            conditions.append(OrderInfo.order_status == order_status)

        if payment_status:
            conditions.append(OrderInfo.payment_status == payment_status)

        if fulfillment_status:
            conditions.append(OrderInfo.fulfillment_status == fulfillment_status)

        count_stmt = select(func.count()).select_from(OrderInfo).where(*conditions)
        total = await db.scalar(count_stmt)
        total = int(total or 0)

        stmt = (
            select(OrderInfo)
            .where(*conditions)
            .order_by(OrderInfo.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all()), total

    async def get_by_order_no(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            order_no: str,
            include_items: bool = False,
    ) -> OrderInfo | None:
        stmt = (
            select(OrderInfo)
            .where(
                OrderInfo.tenant_id == tenant_id,
                OrderInfo.order_no == order_no,
                OrderInfo.deleted_at.is_(None),
            )
        )

        if include_items:
            stmt = stmt.options(selectinload(OrderInfo.items))

        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            order_id: UUID,
            include_items: bool = False,
    ) -> OrderInfo | None:
        stmt = (
            select(OrderInfo)
            .where(
                OrderInfo.tenant_id == tenant_id,
                OrderInfo.id == order_id,
                OrderInfo.deleted_at.is_(None),
            )
        )

        if include_items:
            stmt = stmt.options(selectinload(OrderInfo.items))

        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_item_by_id(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            order_item_id: UUID,
    ) -> OrderItem | None:
        stmt = (
            select(OrderItem)
            .where(
                OrderItem.tenant_id == tenant_id,
                OrderItem.id == order_item_id,
                OrderItem.deleted_at.is_(None),
            )
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
