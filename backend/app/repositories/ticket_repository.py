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

from app.models.ticket import CustomerServiceTicket


class CustomerServiceTicketRepository:
    """
    客服工单数据访问层。
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
            category: str | None = None,
            priority: str | None = None,
    ) -> tuple[list[CustomerServiceTicket], int]:
        conditions = [
            CustomerServiceTicket.tenant_id == tenant_id,
            CustomerServiceTicket.deleted_at.is_(None),
        ]

        if user_id:
            conditions.append(CustomerServiceTicket.user_id == user_id)

        if order_id:
            conditions.append(CustomerServiceTicket.order_id == order_id)

        if status:
            conditions.append(CustomerServiceTicket.status == status)

        if category:
            conditions.append(CustomerServiceTicket.category == category)

        if priority:
            conditions.append(CustomerServiceTicket.priority == priority)

        count_stmt = (
            select(func.count())
            .select_from(CustomerServiceTicket)
            .where(*conditions)
        )
        total = await db.scalar(count_stmt)
        total = int(total or 0)

        stmt = (
            select(CustomerServiceTicket)
            .where(*conditions)
            .order_by(CustomerServiceTicket.created_at.desc())
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
    ) -> CustomerServiceTicket | None:
        stmt = (
            select(CustomerServiceTicket)
            .where(
                CustomerServiceTicket.tenant_id == tenant_id,
                CustomerServiceTicket.ticket_no == ticket_no,
                CustomerServiceTicket.deleted_at.is_(None),
            )
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
            self,
            db: AsyncSession,
            *,
            ticket: CustomerServiceTicket,
    ) -> CustomerServiceTicket:
        db.add(ticket)
        await db.flush()
        await db.refresh(ticket)
        return ticket
