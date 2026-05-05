# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/05/05 08:52
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
import asyncio
import os
from uuid import UUID

import httpx
import pytest
from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import AsyncSessionLocal, engine
from app.models.auth import AuthAccount
from app.models.user import UserProfile

BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8002")
TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")


async def _get_user_by_user_no(session, user_no: str) -> UserProfile:
    stmt = select(UserProfile).where(
        UserProfile.tenant_id == TENANT_ID,
        UserProfile.user_no == user_no,
        UserProfile.deleted_at.is_(None),
    )
    user = (await session.execute(stmt)).scalar_one_or_none()
    if user is None:
        raise RuntimeError(f"missing seed user: {user_no}")
    return user


async def _ensure_auth_accounts() -> None:
    await _upsert_account("admin", "admin123", "admin", "U100001")
    await _upsert_account("operator", "operator123", "operator", "U100001")
    await _upsert_account("viewer", "viewer123", "viewer", "U200001")

    # 避免 asyncpg 连接被保留在已关闭的 asyncio loop 中，
    # 导致后续 async 数据库测试复用旧连接时报 event loop is closed。
    await engine.dispose()


async def _upsert_account(username: str, password: str, role: str, user_no: str) -> None:
    async with AsyncSessionLocal() as session:
        user = await _get_user_by_user_no(session, user_no)

        stmt = select(AuthAccount).where(
            AuthAccount.tenant_id == TENANT_ID,
            AuthAccount.username == username,
            AuthAccount.deleted_at.is_(None),
        )
        account = (await session.execute(stmt)).scalar_one_or_none()

        if account is None:
            account = AuthAccount(
                tenant_id=TENANT_ID,
                user_id=user.id,
                username=username,
                password_hash=hash_password(password),
                role=role,
                status="active",
            )
            session.add(account)
        else:
            account.user_id = user.id
            account.password_hash = hash_password(password)
            account.role = role
            account.status = "active"

        await session.commit()


@pytest.fixture(scope="module", autouse=True)
def ensure_auth_accounts():
    asyncio.run(_ensure_auth_accounts())


def test_login_should_return_access_token():
    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "admin",
                "password": "admin123",
            },
        )

    assert response.status_code == 200
    body = response.json()

    assert body["success"] is True
    assert body["code"] == "OK"
    assert body["data"]["access_token"]
    assert body["data"]["token_type"] == "bearer"
    assert body["data"]["expires_in"] > 0
    assert body["data"]["user"]["username"] == "admin"
    assert body["data"]["user"]["role"] == "admin"
    assert body["data"]["user"]["user_no"] == "U100001"
    assert body["data"]["user"]["tenant_id"] == str(TENANT_ID)


def test_login_should_reject_wrong_password():
    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "admin",
                "password": "wrong-password",
            },
        )

    assert response.status_code == 401
    body = response.json()

    assert body["success"] is False
    assert body["code"] == "UNAUTHORIZED"


def test_auth_me_should_return_current_user():
    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "admin",
                "password": "admin123",
            },
        )
        token = login_response.json()["data"]["access_token"]

        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    body = response.json()

    assert body["success"] is True
    assert body["data"]["user"]["username"] == "admin"
    assert body["data"]["user"]["role"] == "admin"
    assert body["data"]["user"]["user_no"] == "U100001"
    assert body["data"]["user"]["tenant_id"] == str(TENANT_ID)


def test_auth_me_should_reject_missing_token():
    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    body = response.json()

    assert body["success"] is False
    assert body["code"] == "UNAUTHORIZED"
