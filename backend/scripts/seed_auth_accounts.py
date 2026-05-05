# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/05/05 08:44
IDE       :PyCharm
作者      :董宏升

认证账号种子数据。

用途：
- 为窗口 13 提供本地 demo / test 登录账号；
- 不存储明文密码到数据库；
- 密码只在本地 seed 脚本中作为 demo 输入，经 hash 后写入 auth_account。

默认账号：
- admin / admin123
- operator / operator123
- viewer / viewer123

注意：
这些是本地开发和演示账号，不是生产账号。
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
import asyncio
import os
from uuid import UUID

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.models.auth import AuthAccount
from app.models.user import UserProfile

TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")

DEMO_ACCOUNTS = [
    {
        "username": "admin",
        "password": os.getenv("AUTH_SEED_ADMIN_PASSWORD", "admin123"),
        "role": "admin",
        "user_no": "U100001",
    },
    {
        "username": "operator",
        "password": os.getenv("AUTH_SEED_OPERATOR_PASSWORD", "operator123"),
        "role": "operator",
        "user_no": "U100001",
    },
    {
        "username": "viewer",
        "password": os.getenv("AUTH_SEED_VIEWER_PASSWORD", "viewer123"),
        "role": "viewer",
        "user_no": "U200001",
    },
]


async def get_user_by_user_no(session, user_no: str) -> UserProfile:
    stmt = select(UserProfile).where(
        UserProfile.tenant_id == TENANT_ID,
        UserProfile.user_no == user_no,
        UserProfile.deleted_at.is_(None),
    )
    user = (await session.execute(stmt)).scalar_one_or_none()
    if user is None:
        raise RuntimeError(f"UserProfile not found: {user_no}")
    return user


async def upsert_auth_account(session, account_data: dict) -> None:
    user = await get_user_by_user_no(session, account_data["user_no"])

    stmt = select(AuthAccount).where(
        AuthAccount.tenant_id == TENANT_ID,
        AuthAccount.username == account_data["username"],
        AuthAccount.deleted_at.is_(None),
    )
    account = (await session.execute(stmt)).scalar_one_or_none()

    if account is None:
        account = AuthAccount(
            tenant_id=TENANT_ID,
            user_id=user.id,
            username=account_data["username"],
            password_hash=hash_password(account_data["password"]),
            role=account_data["role"],
            status="active",
        )
        session.add(account)
        action = "created"
    else:
        account.user_id = user.id
        account.password_hash = hash_password(account_data["password"])
        account.role = account_data["role"]
        account.status = "active"
        action = "updated"

    print(
        f"{action}: username={account_data['username']}, "
        f"role={account_data['role']}, user_no={account_data['user_no']}"
    )


async def main() -> None:
    async with AsyncSessionLocal() as session:
        for account_data in DEMO_ACCOUNTS:
            await upsert_auth_account(session, account_data)

        await session.commit()

    print("auth account seed completed")


if __name__ == "__main__":
    asyncio.run(main())
