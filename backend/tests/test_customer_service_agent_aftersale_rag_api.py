# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/05/03 09:52
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
import os
from uuid import UUID

import httpx

BASE_URL = (
        os.getenv("TEST_API_BASE_URL")
        or os.getenv("API_BASE_URL")
        or "http://127.0.0.1:8000"
)

TENANT_ID = "00000000-0000-0000-0000-000000000001"

# 如果你本地 seed 售后单号不是 AS100001，先用数据库查一下后替换。
SEED_AFTER_SALE_TICKET_NO = "AS100001"

# 来自窗口 3 seed 订单明细。
SEED_ORDER_NO = "O100001"
SEED_USER_NO = "U100001"
SEED_ORDER_ITEM_ID = "31000000-0000-0000-0000-000000000001"


def api_post(path: str, json: dict) -> httpx.Response:
    return httpx.post(
        f"{BASE_URL}{path}",
        json=json,
        timeout=30.0,
        trust_env=False,
    )


def test_customer_service_agent_aftersale_detail_query() -> None:
    """售后单查询：提供 after_sale_ticket_no，应调用 get_aftersale_detail。"""

    payload = {
        "tenant_id": TENANT_ID,
        "session_id": "test_cs_aftersale_detail_session_001",
        "user_no": SEED_USER_NO,
        "message": f"帮我查一下售后单 {SEED_AFTER_SALE_TICKET_NO} 的进度",
        "conversation_summary": "",
        "context": {
            "after_sale_ticket_no": SEED_AFTER_SALE_TICKET_NO,
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
    assert data["intent"] == "aftersale_query"
    assert data["handoff_required"] is False

    tool_calls = data["tool_calls"]
    tool_names = [item["tool_name"] for item in tool_calls]

    assert "get_aftersale_detail" in tool_names

    detail_call = next(
        item for item in tool_calls if item["tool_name"] == "get_aftersale_detail"
    )
    assert detail_call["success"] is True
    assert detail_call["error_code"] is None


def test_customer_service_agent_aftersale_apply_missing_info() -> None:
    """售后申请信息不足：只说我要退款，不允许直接创建售后单。"""

    payload = {
        "tenant_id": TENANT_ID,
        "session_id": "test_cs_aftersale_missing_session_001",
        "user_no": SEED_USER_NO,
        "message": "我要退款",
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
    assert data["intent"] == "aftersale_apply"
    assert data["handoff_required"] is False

    tool_calls = data["tool_calls"]
    tool_names = [item["tool_name"] for item in tool_calls]

    assert "create_aftersale_ticket" not in tool_names
    assert data["answer"]
    assert (
            "补充" in data["answer"]
            or "订单号" in data["answer"]
            or "order_no" in data["answer"]
            or "order_item_id" in data["answer"]
    )

    metadata = data["metadata"]
    assert metadata.get("aftersale_mode") == "need_more_info"
    assert metadata.get("missing_fields")


def test_customer_service_agent_aftersale_apply_complete_info() -> None:
    """售后申请信息齐全：允许 create_aftersale_ticket。"""

    payload = {
        "tenant_id": TENANT_ID,
        "session_id": "test_cs_aftersale_create_session_001",
        "user_no": SEED_USER_NO,
        "message": "我要退款，商品不想要了",
        "conversation_summary": "",
        "context": {
            "user_no": SEED_USER_NO,
            "order_no": SEED_ORDER_NO,
            "order_item_id": SEED_ORDER_ITEM_ID,
            "after_sale_type": "refund",
            "reason": "商品不想要了，申请退款",
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
    assert data["intent"] == "aftersale_apply"

    tool_calls = data["tool_calls"]
    tool_names = [item["tool_name"] for item in tool_calls]

    assert "create_aftersale_ticket" in tool_names

    create_call = next(
        item for item in tool_calls if item["tool_name"] == "create_aftersale_ticket"
    )
    assert create_call["success"] is True
    assert create_call["error_code"] is None

    assert data["metadata"].get("aftersale_mode") == "create"


def test_customer_service_agent_policy_rag_with_citations() -> None:
    """政策问答：七天无理由退货政策应调用 RAG，并尽量返回 citations。"""

    payload = {
        "tenant_id": TENANT_ID,
        "session_id": "test_cs_policy_rag_session_001",
        "user_no": SEED_USER_NO,
        "message": "七天无理由退货政策是什么？",
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
    assert data["intent"] == "policy_query"

    tool_calls = data["tool_calls"]
    tool_names = [item["tool_name"] for item in tool_calls]

    assert "rag_policy_ask" in tool_names

    rag_call = next(
        item for item in tool_calls if item["tool_name"] == "rag_policy_ask"
    )
    assert rag_call["success"] is True

    # 总控要求：正常政策问答需要返回 citations。
    assert isinstance(data["citations"], list)
    assert len(data["citations"]) > 0

    assert data["handoff_required"] is False


def test_customer_service_agent_policy_rag_without_citations_should_be_safe() -> None:
    """政策问答无 citations 时：必须转人工或谨慎处理。"""

    payload = {
        "tenant_id": TENANT_ID,
        "session_id": "test_cs_policy_no_citation_session_001",
        "user_no": SEED_USER_NO,
        "message": "七天无理由退货政策里关于火星仓库跨星际退货的规则是什么？",
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
    assert data["intent"] == "policy_query"

    tool_calls = data["tool_calls"]
    tool_names = [item["tool_name"] for item in tool_calls]

    assert "rag_policy_ask" in tool_names

    if not data["citations"]:
        assert data["handoff_required"] is True
        assert (
                "政策" in (data["handoff_reason"] or "")
                or "引用" in (data["handoff_reason"] or "")
                or "人工" in data["answer"]
                or "核实" in data["answer"]
        )
    else:
        assert data["handoff_required"] is False
