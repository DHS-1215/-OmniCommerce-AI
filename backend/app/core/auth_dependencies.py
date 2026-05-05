# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/05/05 08:39
IDE       :PyCharm
作者      :董宏升

认证与 RBAC 依赖。

核心原则：
- AUTH_ENABLED=false 时，旧接口不因为缺 token 被卡住；
- AUTH_ENABLED=true 时，关键接口必须校验 token / role / tenant；
- /auth/me 这种认证接口使用 require_current_user，始终要求 Bearer Token。
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.core.security import decode_access_token
from app.db.session import get_db_session
from app.services.auth_service import AuthService

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CurrentUser:
    account_id: UUID
    user_id: UUID
    user_no: str
    username: str
    tenant_id: UUID
    role: str


def _claims_to_uuid(claims: dict, key: str) -> UUID:
    value = claims.get(key)
    if not value:
        raise UnauthorizedException("Invalid token")
    try:
        return UUID(str(value))
    except ValueError as exc:
        raise UnauthorizedException("Invalid token") from exc


async def _load_user_from_credentials(
        request: Request,
        credentials: HTTPAuthorizationCredentials,
        session: AsyncSession,
) -> CurrentUser:
    try:
        claims = decode_access_token(credentials.credentials)
    except ValueError as exc:
        raise UnauthorizedException("Invalid or expired token") from exc

    account_id = _claims_to_uuid(claims, "account_id")
    user_id = _claims_to_uuid(claims, "user_id")
    tenant_id = _claims_to_uuid(claims, "tenant_id")
    role = claims.get("role")
    user_no = claims.get("user_no")

    if role not in {"admin", "operator", "viewer"}:
        raise UnauthorizedException("Invalid token")

    if not user_no:
        raise UnauthorizedException("Invalid token")

    account = await AuthService(session).get_account_by_id(account_id)
    if account is None:
        raise UnauthorizedException("Invalid token")

    if account.status != "active":
        raise ForbiddenException("Account is disabled")

    if account.user_id != user_id or account.tenant_id != tenant_id or account.role != role:
        raise UnauthorizedException("Invalid token")

    if account.user is None or account.user.deleted_at is not None:
        raise UnauthorizedException("Invalid token")

    current_user = CurrentUser(
        account_id=account.id,
        user_id=account.user_id,
        user_no=account.user.user_no,
        username=account.username,
        tenant_id=account.tenant_id,
        role=account.role,
    )

    request.state.user_id = str(current_user.user_id)
    request.state.tenant_id = str(current_user.tenant_id)

    return current_user


async def get_current_user(
        request: Request,
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
        session: AsyncSession = Depends(get_db_session),
) -> CurrentUser | None:
    """
    兼容型 current_user。

    - AUTH_ENABLED=false 且无 token：返回 None，保证旧接口不炸；
    - AUTH_ENABLED=true 且无 token：返回 401；
    - 只要传了 token，无论 AUTH_ENABLED 是否开启，都尝试解析。
    """

    settings = get_settings()

    if credentials is None:
        if settings.auth_enabled:
            raise UnauthorizedException("Missing bearer token")
        return None

    return await _load_user_from_credentials(
        request=request,
        credentials=credentials,
        session=session,
    )


async def require_current_user(
        request: Request,
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
        session: AsyncSession = Depends(get_db_session),
) -> CurrentUser:
    """
    强制认证型 current_user。

    /auth/me 使用该依赖。
    """

    if credentials is None:
        raise UnauthorizedException("Missing bearer token")

    return await _load_user_from_credentials(
        request=request,
        credentials=credentials,
        session=session,
    )


async def get_current_tenant_id(
        current_user: CurrentUser | None = Depends(get_current_user),
) -> UUID | None:
    if current_user is None:
        return None
    return current_user.tenant_id


def require_roles(*roles: str):
    """
    RBAC 角色依赖。

    AUTH_ENABLED=false：
    - no-op，返回 None，兼容旧接口和旧测试。

    AUTH_ENABLED=true：
    - 必须有 token；
    - 当前用户角色必须在 roles 内。
    """

    allowed_roles = set(roles)

    async def dependency(
            current_user: CurrentUser | None = Depends(get_current_user),
    ) -> CurrentUser | None:
        settings = get_settings()

        if not settings.auth_enabled:
            return current_user

        if current_user is None:
            raise UnauthorizedException("Missing bearer token")

        if current_user.role not in allowed_roles:
            raise ForbiddenException("Permission denied")

        return current_user

    return dependency


def ensure_tenant_allowed(
        provided_tenant_id: UUID | str | None,
        current_user: CurrentUser | None,
) -> UUID | None:
    """
    tenant_id 一致性校验。

    使用方式：
    - AUTH_ENABLED=false：返回 provided_tenant_id，不做限制；
    - AUTH_ENABLED=true：以 token tenant_id 为准；
    - 如果请求也传了 tenant_id，必须与 token tenant_id 一致。
    """

    settings = get_settings()

    if not settings.auth_enabled:
        if provided_tenant_id is None:
            return None
        return UUID(str(provided_tenant_id))

    if current_user is None:
        raise UnauthorizedException("Missing bearer token")

    if provided_tenant_id is not None and UUID(str(provided_tenant_id)) != current_user.tenant_id:
        raise ForbiddenException("Tenant mismatch")

    return current_user.tenant_id
