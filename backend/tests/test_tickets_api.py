# -*- coding: utf-8 -*-
from __future__ import annotations

import os
from uuid import uuid4

import httpx

BASE_URL = (
    os.getenv("TEST_API_BASE_URL")
    or os.getenv("API_BASE_URL")
    or "http://127.0.0.1:8000"
)
TENANT_ID = "00000000-0000-0000-0000-000000000001"


def api_get(path: str, *, params: dict | None = None) -> httpx.Response:
    return httpx.get(
        f"{BASE_URL}{path}",
        params=params,
        timeout=10.0,
        trust_env=False,
    )


def api_post(path: str, *, json: dict) -> httpx.Response:
    return httpx.post(
        f"{BASE_URL}{path}",
        json=json,
        timeout=10.0,
        trust_env=False,
    )


def test_list_customer_service_tickets_success() -> None:
    response = api_get(
        "/api/v1/tickets",
        params={
            "tenant_id": TENANT_ID,
            "page": 1,
            "page_size": 20,
        },
    )

    assert response.status_code == 200
    body = response.json()

    assert body["success"] is True
    assert body["code"] == "OK"
    assert "items" in body["data"]
    assert body["data"]["total"] >= 1


def test_get_customer_service_ticket_detail_success() -> None:
    response = api_get(
        "/api/v1/tickets/CS100001",
        params={"tenant_id": TENANT_ID},
    )

    assert response.status_code == 200
    body = response.json()

    assert body["success"] is True
    assert body["code"] == "OK"
    assert body["data"]["ticket_no"] == "CS100001"


def test_create_customer_service_ticket_success() -> None:
    trace_id = uuid4().hex[:8]
    payload = {
        "tenant_id": TENANT_ID,
        "user_no": "U100001",
        "order_no": "O100001",
        "source": "api",
        "channel": "web",
        "category": "complaint",
        "priority": "high",
        "title": f"自动化测试客服工单-{trace_id}",
        "content": "窗口 3 自动化测试创建客服工单",
        "assigned_operator_id": None,
        "metadata_json": {
            "source": "window3_api_test",
            "trace_id": trace_id,
        },
    }

    response = api_post("/api/v1/tickets", json=payload)

    assert response.status_code == 201
    body = response.json()

    assert body["success"] is True
    assert body["code"] == "OK"
    assert body["message"] == "created"
    assert body["data"]["ticket_no"].startswith("CS")
    assert body["data"]["status"] == "open"
    assert body["data"]["source"] == "api"
    assert body["data"]["category"] == "complaint"
    assert body["data"]["priority"] == "high"


def test_get_customer_service_ticket_detail_not_found() -> None:
    response = api_get(
        "/api/v1/tickets/NO_TICKET",
        params={"tenant_id": TENANT_ID},
    )

    assert response.status_code == 404
    body = response.json()

    assert body["success"] is False
    assert body["code"] == "CUSTOMER_SERVICE_TICKET_NOT_FOUND"


def test_create_customer_service_ticket_order_not_found() -> None:
    payload = {
        "tenant_id": TENANT_ID,
        "user_no": "U100001",
        "order_no": "NO_ORDER",
        "source": "api",
        "channel": "web",
        "category": "complaint",
        "priority": "high",
        "title": "自动化测试客服工单",
        "content": "订单不存在测试",
        "assigned_operator_id": None,
        "metadata_json": {
            "source": "window3_api_test",
        },
    }

    response = api_post("/api/v1/tickets", json=payload)

    assert response.status_code == 404
    body = response.json()

    assert body["success"] is False
    assert body["code"] == "ORDER_NOT_FOUND"


def test_tickets_invalid_tenant_id() -> None:
    response = api_get(
        "/api/v1/tickets",
        params={"tenant_id": "bad-tenant-id"},
    )

    assert response.status_code == 422
    body = response.json()

    assert body["success"] is False
    assert body["code"] == "VALIDATION_ERROR"