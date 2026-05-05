# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/05/05 08:40
IDE       :PyCharm
作者      :董宏升

认证 API。
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_dependencies import CurrentUser, require_current_user
from app.core.response import success_response
from app.db.session import get_db_session
from app.schemas.auth import AuthUserInfo, LoginRequest, MeResponse
from app.services.auth_service import AuthService

router = APIRouter()


@router.post("/login")
async def login(
        payload: LoginRequest,
        request: Request,
        session: AsyncSession = Depends(get_db_session),
):
    service = AuthService(session)
    result = await service.login(
        username=payload.username,
        password=payload.password,
        tenant_id=payload.tenant_id,
    )

    return success_response(
        data=result.model_dump(mode="json"),
        request_id=getattr(request.state, "request_id", None),
    )


@router.get("/me")
async def me(
        request: Request,
        current_user: CurrentUser = Depends(require_current_user),
):
    result = MeResponse(
        user=AuthUserInfo(
            account_id=current_user.account_id,
            user_id=current_user.user_id,
            user_no=current_user.user_no,
            username=current_user.username,
            tenant_id=current_user.tenant_id,
            role=current_user.role,
        )
    )

    return success_response(
        data=result.model_dump(mode="json"),
        request_id=getattr(request.state, "request_id", None),
    )
