# -*- coding: utf-8 -*-
from __future__ import annotations

import os

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


def test_list_orders_success() -> None:
    response = api_get(
        "/api/v1/orders",
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

    order_nos = {item["order_no"] for item in body["data"]["items"]}
    assert "O100001" in order_nos


def test_list_orders_by_user_success() -> None:
    response = api_get(
        "/api/v1/orders",
        params={
            "tenant_id": TENANT_ID,
            "user_no": "U100001",
            "page": 1,
            "page_size": 20,
        },
    )

    assert response.status_code == 200
    body = response.json()

    assert body["success"] is True
    assert body["code"] == "OK"
    assert body["data"]["total"] >= 1

    order_nos = {item["order_no"] for item in body["data"]["items"]}
    assert "O100001" in order_nos


def test_get_order_detail_success() -> None:
    response = api_get(
        "/api/v1/orders/O100001",
        params={"tenant_id": TENANT_ID},
    )

    assert response.status_code == 200
    body = response.json()

    assert body["success"] is True
    assert body["code"] == "OK"
    assert body["data"]["order_no"] == "O100001"
    assert isinstance(body["data"]["items"], list)
    assert len(body["data"]["items"]) >= 1


def test_get_order_detail_not_found() -> None:
    response = api_get(
        "/api/v1/orders/NO_ORDER",
        params={"tenant_id": TENANT_ID},
    )

    assert response.status_code == 404
    body = response.json()

    assert body["success"] is False
    assert body["code"] == "ORDER_NOT_FOUND"


def test_list_orders_user_not_found() -> None:
    response = api_get(
        "/api/v1/orders",
        params={
            "tenant_id": TENANT_ID,
            "user_no": "NO_USER",
            "page": 1,
            "page_size": 20,
        },
    )

    assert response.status_code == 404
    body = response.json()

    assert body["success"] is False
    assert body["code"] == "USER_NOT_FOUND"


def test_orders_invalid_tenant_id() -> None:
    response = api_get(
        "/api/v1/orders",
        params={"tenant_id": "bad-tenant-id"},
    )

    assert response.status_code == 422
    body = response.json()

    assert body["success"] is False
    assert body["code"] == "VALIDATION_ERROR"
