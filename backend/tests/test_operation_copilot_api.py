# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/05/04 09:00
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
import os
from typing import Any

import httpx

BASE_URL = os.getenv("TEST_API_BASE_URL", os.getenv("API_BASE_URL", "http://127.0.0.1:8000"))
TENANT_ID = "00000000-0000-0000-0000-000000000001"


def _post_operation_copilot(payload: dict[str, Any]) -> dict[str, Any]:
    with httpx.Client(base_url=BASE_URL, timeout=30.0, trust_env=False) as client:
        response = client.post("/api/v1/agents/operation-copilot/chat", json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True
    return body["data"]


def test_operation_copilot_query_gmv() -> None:
    data = _post_operation_copilot(
        {
            "tenant_id": TENANT_ID,
            "session_id": "op_test_gmv_001",
            "user_no": "U100001",
            "message": "帮我查询一下 GMV",
            "conversation_summary": "",
            "context": {
                "metric_key": "gmv",
            },
        }
    )

    assert data["intent"] == "metric_query"
    assert data["agent_task_id"]
    assert data["sql_summary"]["guard"]["passed"] is True
    assert data["query_result"]["row_count"] == 1
    assert "gmv" in data["query_result"]["columns"]
    assert "SQL Guard" in data["answer"]


def test_operation_copilot_query_inventory() -> None:
    data = _post_operation_copilot(
        {
            "tenant_id": TENANT_ID,
            "session_id": "op_test_inventory_001",
            "user_no": "U100001",
            "message": "帮我看一下库存情况，尤其是低库存 SKU",
            "conversation_summary": "",
            "context": {
                "metric_key": "low_stock_sku_count",
            },
        }
    )

    assert data["intent"] == "metric_query"
    assert data["sql_summary"]["guard"]["passed"] is True
    assert data["query_result"]["row_count"] == 1
    assert "low_stock_sku_count" in data["query_result"]["columns"]


def test_operation_copilot_conversion_rate_data_source_missing() -> None:
    data = _post_operation_copilot(
        {
            "tenant_id": TENANT_ID,
            "session_id": "op_test_conversion_001",
            "user_no": "U100001",
            "message": "帮我分析一下转化率",
            "conversation_summary": "",
            "context": {
                "metric_key": "conversion_rate",
            },
        }
    )

    assert data["intent"] == "metric_query"
    assert data["query_result"] is None
    assert data["sql_summary"]["guard"]["error_code"] == "SQL_NOT_GENERATED"
    assert "不能用订单数或用户数伪造转化率" in data["answer"]


def test_operation_copilot_report_based_on_query_result() -> None:
    data = _post_operation_copilot(
        {
            "tenant_id": TENANT_ID,
            "session_id": "op_test_report_001",
            "user_no": "U100001",
            "message": "帮我做一个 GMV 运营分析报告",
            "conversation_summary": "",
            "context": {
                "metric_key": "gmv",
            },
        }
    )

    assert data["intent"] == "operation_report"
    assert data["query_result"] is not None
    assert data["metadata"]["report_generation_boundary"]
