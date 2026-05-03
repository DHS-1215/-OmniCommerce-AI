# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/27 16:51
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import UserProfile


class UserRepository:
    """
    用户画像数据访问层。
    """

    async def get_by_id(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            user_id: UUID,
    ) -> UserProfile | None:
        stmt = (
            select(UserProfile)
            .where(
                UserProfile.tenant_id == tenant_id,
                UserProfile.id == user_id,
                UserProfile.deleted_at.is_(None),
            )
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_user_no(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            user_no: str,
    ) -> UserProfile | None:
        stmt = (
            select(UserProfile)
            .where(
                UserProfile.tenant_id == tenant_id,
                UserProfile.user_no == user_no,
                UserProfile.deleted_at.is_(None),
            )
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()


