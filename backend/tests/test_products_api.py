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


def test_list_products_success() -> None:
    response = api_get(
        "/api/v1/products",
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

    product_nos = {item["product_no"] for item in body["data"]["items"]}
    assert "P100001" in product_nos


def test_get_product_detail_success() -> None:
    response = api_get(
        "/api/v1/products/P100001",
        params={"tenant_id": TENANT_ID},
    )

    assert response.status_code == 200
    body = response.json()

    assert body["success"] is True
    assert body["code"] == "OK"
    assert body["data"]["product_no"] == "P100001"
    assert isinstance(body["data"]["skus"], list)
    assert len(body["data"]["skus"]) >= 1


def test_list_product_skus_success() -> None:
    response = api_get(
        "/api/v1/products/P100001/skus",
        params={"tenant_id": TENANT_ID},
    )

    assert response.status_code == 200
    body = response.json()

    assert body["success"] is True
    assert body["code"] == "OK"
    assert isinstance(body["data"], list)

    sku_nos = {item["sku_no"] for item in body["data"]}
    assert "SKU100001" in sku_nos


def test_get_sku_detail_success() -> None:
    response = api_get(
        "/api/v1/products/skus/SKU100001",
        params={"tenant_id": TENANT_ID},
    )

    assert response.status_code == 200
    body = response.json()

    assert body["success"] is True
    assert body["code"] == "OK"
    assert body["data"]["sku_no"] == "SKU100001"


def test_list_product_reviews_success() -> None:
    response = api_get(
        "/api/v1/products/P100001/reviews",
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

    review = body["data"]["items"][0]
    assert review["status"] == "visible"
    assert 1 <= review["rating"] <= 5


def test_get_product_detail_not_found() -> None:
    response = api_get(
        "/api/v1/products/NO_PRODUCT",
        params={"tenant_id": TENANT_ID},
    )

    assert response.status_code == 404
    body = response.json()

    assert body["success"] is False
    assert body["code"] == "PRODUCT_NOT_FOUND"


def test_get_sku_detail_not_found() -> None:
    response = api_get(
        "/api/v1/products/skus/NO_SKU",
        params={"tenant_id": TENANT_ID},
    )

    assert response.status_code == 404
    body = response.json()

    assert body["success"] is False
    assert body["code"] == "SKU_NOT_FOUND"


def test_products_invalid_tenant_id() -> None:
    response = api_get(
        "/api/v1/products",
        params={"tenant_id": "bad-tenant-id"},
    )

    assert response.status_code == 422
    body = response.json()

    assert body["success"] is False
    assert body["code"] == "VALIDATION_ERROR"