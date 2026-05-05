# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/05/05 09:20
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
import pytest
import os
from uuid import UUID

import httpx

BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8002")
TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")
OTHER_TENANT_ID = UUID("00000000-0000-0000-0000-000000000002")
DUMMY_VERSION_ID = UUID("99999999-9999-9999-9999-999999999999")
pytestmark = pytest.mark.skipif(
    os.getenv("AUTH_ENABLED", "false").lower() != "true",
    reason="RBAC API tests require backend service running with AUTH_ENABLED=true",
)

def _login(username: str, password: str) -> str:
    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": username,
                "password": password,
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True

    return body["data"]["access_token"]


def test_operator_should_be_rejected_by_admin_prompt_write_api():

    token = _login("operator", "operator123")

    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        response = client.post(
            f"/api/v1/prompts/versions/{DUMMY_VERSION_ID}/activate",
            params={"tenant_id": str(TENANT_ID)},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 403
    body = response.json()

    assert body["success"] is False
    assert body["code"] == "FORBIDDEN"


def test_viewer_should_be_rejected_by_admin_prompt_write_api(monkeypatch):

    token = _login("viewer", "viewer123")

    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        response = client.post(
            f"/api/v1/prompts/versions/{DUMMY_VERSION_ID}/activate",
            params={"tenant_id": str(TENANT_ID)},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 403
    body = response.json()

    assert body["success"] is False
    assert body["code"] == "FORBIDDEN"


def test_tenant_mismatch_should_be_rejected_when_auth_enabled(monkeypatch):

    token = _login("admin", "admin123")

    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        response = client.post(
            f"/api/v1/prompts/versions/{DUMMY_VERSION_ID}/activate",
            params={"tenant_id": str(OTHER_TENANT_ID)},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 403
    body = response.json()

    assert body["success"] is False
    assert body["code"] == "FORBIDDEN"
    assert body["message"] == "Tenant mismatch"


def test_admin_should_pass_rbac_before_business_not_found(monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "true")

    token = _login("admin", "admin123")

    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        response = client.post(
            f"/api/v1/prompts/versions/{DUMMY_VERSION_ID}/activate",
            params={"tenant_id": str(TENANT_ID)},
            headers={"Authorization": f"Bearer {token}"},
        )

    # admin 权限和 tenant 校验已经通过，后续进入业务层。
    # dummy version 不存在，因此业务层应返回 404，而不是 401/403。
    assert response.status_code == 404
    body = response.json()

    assert body["success"] is False
    assert body["code"] == "PROMPT_VERSION_NOT_FOUND"
