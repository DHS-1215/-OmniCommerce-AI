from __future__ import annotations

import os
from uuid import UUID

import httpx


BASE_URL = (
    os.getenv("TEST_API_BASE_URL")
    or os.getenv("API_BASE_URL")
    or "http://127.0.0.1:8000"
)

TENANT_ID = "00000000-0000-0000-0000-000000000001"


def api_post(path: str, json: dict) -> httpx.Response:
    return httpx.post(
        f"{BASE_URL}{path}",
        json=json,
        timeout=30.0,
        trust_env=False,
    )


def test_customer_service_agent_order_query() -> None:
    payload = {
        "tenant_id": TENANT_ID,
        "session_id": "test_cs_order_session_001",
        "user_no": "U100001",
        "message": "我的订单 O100001 到哪了？",
        "conversation_summary": "",
        "context": {
            "order_no": "O100001",
        },
    }

    response = api_post(
        "/api/v1/agents/customer-service/chat",
        json=payload,
    )

    assert response.status_code == 200

    body = response.json()
    assert body["success"] is True
    assert body["code"] == "OK"

    data = body["data"]
    assert data["session_id"] == payload["session_id"]
    assert UUID(data["agent_task_id"])
    assert data["intent"] == "order_query"
    assert data["handoff_required"] is False
    assert data["handoff_reason"] is None

    assert data["answer"]
    assert "O100001" in data["answer"]
    assert "已送达" in data["answer"] or "delivered" in data["answer"]

    tool_calls = data["tool_calls"]
    assert len(tool_calls) >= 1
    assert tool_calls[0]["tool_name"] == "get_order_detail"
    assert tool_calls[0]["success"] is True
    assert tool_calls[0]["error_code"] is None


def test_customer_service_agent_product_query() -> None:
    payload = {
        "tenant_id": TENANT_ID,
        "session_id": "test_cs_product_session_001",
        "user_no": "U100001",
        "message": "智营智能恒温电热水壶有哪些规格？",
        "conversation_summary": "",
        "context": {
            "product_no": "P100001",
        },
    }

    response = api_post(
        "/api/v1/agents/customer-service/chat",
        json=payload,
    )

    assert response.status_code == 200

    body = response.json()
    assert body["success"] is True
    assert body["code"] == "OK"

    data = body["data"]
    assert UUID(data["agent_task_id"])
    assert data["intent"] == "product_query"
    assert data["handoff_required"] is False
    assert data["handoff_reason"] is None

    assert data["answer"]
    assert "智营智能恒温电热水壶" in data["answer"]
    assert (
        "规格" in data["answer"]
        or "库存" in data["answer"]
        or "价格" in data["answer"]
    )

    tool_calls = data["tool_calls"]
    tool_names = [item["tool_name"] for item in tool_calls]

    assert "get_product_detail" in tool_names
    assert "list_product_skus" in tool_names

    for item in tool_calls:
        assert item["success"] is True
        assert item["error_code"] is None


def test_customer_service_agent_complaint_handoff() -> None:
    payload = {
        "tenant_id": TENANT_ID,
        "session_id": "test_cs_complaint_session_001",
        "user_no": "U100001",
        "message": "我要投诉，你们不给我赔偿我就曝光",
        "conversation_summary": "",
        "context": {},
    }

    response = api_post(
        "/api/v1/agents/customer-service/chat",
        json=payload,
    )

    assert response.status_code == 200

    body = response.json()
    assert body["success"] is True
    assert body["code"] == "OK"

    data = body["data"]
    assert UUID(data["agent_task_id"])
    assert data["intent"] == "complaint"
    assert data["handoff_required"] is True
    assert data["handoff_reason"] is not None
    assert "高风险" in data["handoff_reason"] or "投诉" in data["handoff_reason"]

    assert data["answer"]
    assert "转人工" in data["answer"]

    tool_calls = data["tool_calls"]
    tool_names = [item["tool_name"] for item in tool_calls]

    assert "create_customer_service_ticket" in tool_names
    assert "list_orders" not in tool_names

    ticket_call = next(
        item
        for item in tool_calls
        if item["tool_name"] == "create_customer_service_ticket"
    )
    assert ticket_call["success"] is True
    assert ticket_call["error_code"] is None