# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/05/05 08:38
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
"""
认证业务服务。

职责：
- 登录账号查询；
- 密码校验；
- 账号状态校验；
- JWT claims 生成；
- last_login_at 更新；
- 测试 / 种子数据所需的轻量账号创建能力。
"""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ConflictException, ForbiddenException, UnauthorizedException
from app.core.security import create_access_token, hash_password, verify_password
from app.core.config import get_settings
from app.models.auth import AuthAccount
from app.models.user import UserProfile
from app.schemas.auth import AuthUserInfo, LoginResponse


class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.settings = get_settings()

    async def authenticate(
            self,
            username: str,
            password: str,
            tenant_id: UUID | None = None,
    ) -> AuthAccount:
        """
        校验用户名和密码。

        注意：
        - 登录失败统一返回 Unauthorized，避免泄露账号是否存在；
        - disabled 账号返回 Forbidden；
        - username 如果跨租户重复，且请求未指定 tenant_id，则视为无法安全确定身份。
        """

        stmt = (
            select(AuthAccount)
            .options(selectinload(AuthAccount.user))
            .where(
                AuthAccount.username == username,
                AuthAccount.deleted_at.is_(None),
            )
        )

        if tenant_id is not None:
            stmt = stmt.where(AuthAccount.tenant_id == tenant_id)

        result = await self.session.execute(stmt)
        accounts = list(result.scalars().all())

        if not accounts:
            raise UnauthorizedException("Invalid username or password")

        if tenant_id is None and len(accounts) > 1:
            raise UnauthorizedException("Invalid username or password")

        account = accounts[0]

        if not verify_password(password, account.password_hash):
            raise UnauthorizedException("Invalid username or password")

        if account.status != "active":
            raise ForbiddenException("Account is disabled")

        if account.user is None or account.user.deleted_at is not None:
            raise UnauthorizedException("Invalid username or password")

        return account

    async def login(
            self,
            username: str,
            password: str,
            tenant_id: UUID | None = None,
    ) -> LoginResponse:
        account = await self.authenticate(
            username=username,
            password=password,
            tenant_id=tenant_id,
        )

        account.last_login_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(account)

        user_no = account.user.user_no

        claims = {
            "sub": str(account.user_id),
            "account_id": str(account.id),
            "user_id": str(account.user_id),
            "user_no": user_no,
            "tenant_id": str(account.tenant_id),
            "role": account.role,
        }
        access_token = create_access_token(claims)
        expires_in = self.settings.jwt_expire_minutes * 60

        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=expires_in,
            user=AuthUserInfo(
                account_id=account.id,
                user_id=account.user_id,
                user_no=user_no,
                username=account.username,
                tenant_id=account.tenant_id,
                role=account.role,
            ),
        )

    async def get_account_by_id(self, account_id: UUID) -> AuthAccount | None:
        stmt = (
            select(AuthAccount)
            .options(selectinload(AuthAccount.user))
            .where(
                AuthAccount.id == account_id,
                AuthAccount.deleted_at.is_(None),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_account(
            self,
            *,
            tenant_id: UUID,
            user_id: UUID,
            username: str,
            password: str,
            role: str,
            status: str = "active",
    ) -> AuthAccount:
        """
        创建登录账号。

        当前不暴露为公开 API，主要用于种子数据和测试。
        """

        if role not in {"admin", "operator", "viewer"}:
            raise ValueError("role must be one of: admin, operator, viewer")

        if status not in {"active", "disabled"}:
            raise ValueError("status must be one of: active, disabled")

        user = await self.session.get(UserProfile, user_id)
        if user is None or user.deleted_at is not None:
            raise ValueError("user does not exist")

        existing_stmt = select(AuthAccount).where(
            AuthAccount.tenant_id == tenant_id,
            AuthAccount.username == username,
            AuthAccount.deleted_at.is_(None),
        )
        existing = (await self.session.execute(existing_stmt)).scalar_one_or_none()
        if existing is not None:
            raise ConflictException("Auth account already exists")

        account = AuthAccount(
            tenant_id=tenant_id,
            user_id=user_id,
            username=username,
            password_hash=hash_password(password),
            role=role,
            status=status,
        )

        self.session.add(account)
        await self.session.commit()
        await self.session.refresh(account)

        return account
