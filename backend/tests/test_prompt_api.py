# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/05/01 12:16
IDE       :PyCharm
作者      :董宏升

Prompt 管理 API 测试。

说明：
- 本测试不使用 FastAPI TestClient；
- 改为请求运行中的 backend 服务；
- 这样与现有 products/orders/tickets/aftersales API 测试保持一致；
- 避免 TestClient + asyncpg 连接池跨事件循环问题。
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
import os
from uuid import UUID

import httpx

TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")

# Docker 容器内 backend 服务监听 8000；
# Windows 宿主机访问 Docker 映射端口时，可设置：
# $env:TEST_API_BASE_URL="http://127.0.0.1:8002"
BASE_URL = (
    os.getenv("TEST_API_BASE_URL")
    or os.getenv("API_BASE_URL")
    or "http://127.0.0.1:8000"
)


def api_get(path: str, *, params: dict | None = None) -> httpx.Response:
    return httpx.get(
        f"{BASE_URL}{path}",
        params=params,
        timeout=10.0,
        trust_env=False,
    )


def api_post(path: str, *, json: dict | None = None) -> httpx.Response:
    return httpx.post(
        f"{BASE_URL}{path}",
        json=json,
        timeout=10.0,
        trust_env=False,
    )


def test_list_prompt_templates() -> None:
    response = api_get(
        "/api/v1/prompts",
        params={
            "tenant_id": str(TENANT_ID),
            "page": 1,
            "page_size": 100,
        },
    )


    assert response.status_code == 200
    body = response.json()

    assert body["success"] is True
    assert body["code"] == "OK"
    assert body["request_id"] is not None

    data = body["data"]
    assert data["total"] >= 1
    assert isinstance(data["items"], list)

    template_keys = {item["template_key"] for item in data["items"]}
    assert "cs_intent_default" in template_keys


def test_get_active_prompt_by_scene() -> None:
    response = api_get(
        "/api/v1/prompts/by-scene/customer_service_intent/active",
        params={"tenant_id": str(TENANT_ID)},
    )

    assert response.status_code == 200
    body = response.json()

    assert body["success"] is True
    assert body["code"] == "OK"

    data = body["data"]
    assert data["template"]["template_key"] == "cs_intent_default"
    assert data["template"]["scene"] == "customer_service_intent"
    assert data["version"]["version"] >= 1
    assert data["version"]["status"] == "active"
    assert data["version"]["is_active"] is True


def test_render_prompt_success() -> None:
    response = api_post(
        "/api/v1/prompts/render",
        json={
            "tenant_id": str(TENANT_ID),
            "scene": "customer_service_intent",
            "variables": {
                "user_message": "我的订单什么时候发货？",
                "conversation_summary": "",
            },
        },
    )

    assert response.status_code == 200
    body = response.json()

    assert body["success"] is True
    assert body["code"] == "OK"

    data = body["data"]
    assert data["template_key"] == "cs_intent_default"
    assert data["scene"] == "customer_service_intent"
    assert data["version"] >= 1
    assert data["template_id"]
    assert data["version_id"]
    assert "我的订单什么时候发货？" in data["rendered_content"]
    assert "{{user_message}}" not in data["rendered_content"]
    assert "{{conversation_summary}}" not in data["rendered_content"]


def test_render_prompt_missing_variable() -> None:
    response = api_post(
        "/api/v1/prompts/render",
        json={
            "tenant_id": str(TENANT_ID),
            "scene": "customer_service_intent",
            "variables": {
                "user_message": "我的订单什么时候发货？",
            },
        },
    )

    assert response.status_code == 400
    body = response.json()

    assert body["success"] is False
    assert body["code"] == "PROMPT_RENDER_VARIABLE_MISSING"
    assert "conversation_summary" in body["data"]["missing_variables"]
    assert body["request_id"] is not None