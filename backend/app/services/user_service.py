# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/27 20:55
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.core.exceptions import BaseAppException
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserProfileResponse


class UserService:
    """
    用户画像业务服务。
    """

    def __init__(self) -> None:
        self.user_repository = UserRepository()

    async def get_user_profile(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            user_no: str,
    ) -> UserProfileResponse:
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

        return UserProfileResponse.model_validate(user)
