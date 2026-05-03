# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/27 21:14
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.helpers import get_request_id, to_response_data
from app.core.response import ApiResponse, success_response
from app.db.session import get_db_session
from app.services.user_service import UserService

router = APIRouter()

user_service = UserService()


@router.get(
    "/{user_no}",
    response_model=ApiResponse,
    summary="查询用户画像",
)
async def get_user_profile(
        request: Request,
        user_no: str = Path(..., description="用户业务编号"),
        tenant_id: UUID = Query(..., description="租户 ID"),
        db: AsyncSession = Depends(get_db_session),
) -> ApiResponse:
    """
    查询用户画像。

    当前窗口 3 暂未实现认证 / RBAC，因此 tenant_id 通过 query 参数显式传入。
    """

    data = await user_service.get_user_profile(
        db,
        tenant_id=tenant_id,
        user_no=user_no,
    )
    return success_response(
        data=to_response_data(data),
        request_id=get_request_id(request),
    )
