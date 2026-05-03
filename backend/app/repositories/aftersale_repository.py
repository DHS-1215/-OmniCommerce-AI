# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/27 20:49
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ticket import AfterSaleTicket


class AfterSaleRepository:
    """
    售后单数据访问层。
    """

    async def list_tickets(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            page: int,
            page_size: int,
            user_id: UUID | None = None,
            order_id: UUID | None = None,
            status: str | None = None,
            after_sale_type: str | None = None,
    ) -> tuple[list[AfterSaleTicket], int]:
        conditions = [
            AfterSaleTicket.tenant_id == tenant_id,
            AfterSaleTicket.deleted_at.is_(None),
        ]

        if user_id:
            conditions.append(AfterSaleTicket.user_id == user_id)

        if order_id:
            conditions.append(AfterSaleTicket.order_id == order_id)

        if status:
            conditions.append(AfterSaleTicket.status == status)

        if after_sale_type:
            conditions.append(AfterSaleTicket.after_sale_type == after_sale_type)

        count_stmt = select(func.count()).select_from(AfterSaleTicket).where(*conditions)
        total = await db.scalar(count_stmt)
        total = int(total or 0)

        stmt = (
            select(AfterSaleTicket)
            .where(*conditions)
            .order_by(AfterSaleTicket.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all()), total

    async def get_by_ticket_no(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            ticket_no: str,
    ) -> AfterSaleTicket | None:
        stmt = (
            select(AfterSaleTicket)
            .where(
                AfterSaleTicket.tenant_id == tenant_id,
                AfterSaleTicket.ticket_no == ticket_no,
                AfterSaleTicket.deleted_at.is_(None),
            )
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
            self,
            db: AsyncSession,
            *,
            ticket: AfterSaleTicket,
    ) -> AfterSaleTicket:
        db.add(ticket)
        await db.flush()
        await db.refresh(ticket)
        return ticket
