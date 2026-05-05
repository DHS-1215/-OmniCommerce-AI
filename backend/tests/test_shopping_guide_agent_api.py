# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/05/03 16:47
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
import os
from decimal import Decimal
from typing import Any

import httpx

BASE_URL = os.getenv(
    "TEST_API_BASE_URL",
    os.getenv("API_BASE_URL", "http://127.0.0.1:8000"),
)

TENANT_ID = "00000000-0000-0000-0000-000000000001"


def _post_shopping_guide(payload: dict[str, Any]) -> dict[str, Any]:
    with httpx.Client(base_url=BASE_URL, timeout=20.0, trust_env=False) as client:
        response = client.post("/api/v1/agents/shopping-guide/chat", json=payload)
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["success"] is True
    assert body["code"] == "OK"
    return body["data"]


def _get_active_product_nos() -> set[str]:
    with httpx.Client(base_url=BASE_URL, timeout=20.0, trust_env=False) as client:
        response = client.get(
            "/api/v1/products",
            params={"tenant_id": TENANT_ID},
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True

    items = body["data"]["items"]
    return {item["product_no"] for item in items}


def _get_active_sku_nos(product_no: str) -> set[str]:
    with httpx.Client(base_url=BASE_URL, timeout=20.0, trust_env=False) as client:
        response = client.get(
            f"/api/v1/products/{product_no}/skus",
            params={"tenant_id": TENANT_ID},
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True

    return {item["sku_no"] for item in body["data"]}


def _assert_recommendations_are_real_active_data(data: dict[str, Any]) -> None:
    active_product_nos = _get_active_product_nos()

    recommendations = data["recommendations"]
    assert recommendations, "recommendations should not be empty"

    for item in recommendations:
        product_no = item["product_no"]

        assert product_no in active_product_nos
        assert product_no != "P200001"
        assert not product_no.startswith("LLM_")
        assert not product_no.startswith("MOCK_")
        assert product_no != "P_NOT_EXIST"

        active_sku_nos = _get_active_sku_nos(product_no)
        matched_skus = item.get("matched_skus") or []
        assert matched_skus, "each recommendation should include matched_skus"

        for sku in matched_skus:
            sku_no = sku["sku_no"]

            assert sku_no in active_sku_nos
            assert sku_no != "SKU200001"
            assert not sku_no.startswith("LLM_")
            assert not sku_no.startswith("MOCK_")
            assert sku_no != "SKU_NOT_EXIST"

            assert sku["status"] == "active"


def _assert_match_evidence(item: dict[str, Any]) -> None:
    evidence = item.get("match_evidence") or {}

    assert "budget_match" in evidence
    assert "scenario_match" in evidence
    assert "preference_match" in evidence
    assert "stock_risk" in evidence
    assert "review_risk" in evidence

    assert isinstance(evidence["budget_match"]["matched"], bool)
    assert evidence["budget_match"]["reason"]

    assert isinstance(evidence["scenario_match"]["matched"], bool)
    assert evidence["scenario_match"]["reason"]

    assert isinstance(evidence["preference_match"]["matched"], bool)
    assert evidence["preference_match"]["reason"]

    assert evidence["stock_risk"]["level"]
    assert evidence["stock_risk"]["reason"]

    assert evidence["review_risk"]["level"]
    assert evidence["review_risk"]["reason"]

    assert item.get("recommendation_reason")


def test_shopping_guide_recommend_by_budget() -> None:
    payload = {
        "tenant_id": TENANT_ID,
        "session_id": "sg_test_budget_001",
        "user_no": "U100001",
        "message": "我预算 300 元以内，想买一个适合办公室用的智能小家电，最好安全、省心、评价好一点",
        "conversation_summary": "",
        "context": {
            "budget_max": 300,
            "scenario": "office",
            "preferences": ["安全", "省心", "评价好"],
        },
    }

    data = _post_shopping_guide(payload)

    assert data["intent"] == "shopping_guide"
    assert data["agent_task_id"]
    assert data["metadata"]["agent_type"] == "shopping_guide"
    assert data["recommendations"]
    assert data["answer"]

    _assert_recommendations_are_real_active_data(data)

    for item in data["recommendations"]:
        _assert_match_evidence(item)
        score_breakdown = item.get("score_breakdown") or {}

        assert "budget_score" in score_breakdown
        assert "scenario_score" in score_breakdown
        assert "preference_score" in score_breakdown
        assert "stock_score" in score_breakdown
        assert "review_score" in score_breakdown
        assert "total_score" in score_breakdown

        assert isinstance(score_breakdown["total_score"], int)
        assert 0 <= score_breakdown["total_score"] <= 100

        for key in [
            "budget_score",
            "scenario_score",
            "preference_score",
            "stock_score",
            "review_score",
        ]:
            assert isinstance(score_breakdown[key]["score"], int)
            assert score_breakdown[key]["reason"]

        for sku in item["matched_skus"]:
            assert Decimal(str(sku["sale_price"])) <= Decimal("300")
            assert sku["within_budget"] is True


def test_shopping_guide_recommend_by_scenario_and_preference() -> None:
    payload = {
        "tenant_id": TENANT_ID,
        "session_id": "sg_test_scenario_001",
        "user_no": "U100001",
        "message": "我想买适合办公室使用、方便省心的产品",
        "conversation_summary": "",
        "context": {
            "scenario": "office",
            "preferences": ["省心"],
        },
    }

    data = _post_shopping_guide(payload)

    assert data["intent"] == "shopping_guide"
    assert data["scenario"] == "office"
    assert data["recommendations"]

    top = data["recommendations"][0]
    _assert_match_evidence(top)

    assert top["match_evidence"]["scenario_match"]["matched"] is True
    assert top["match_evidence"]["preference_match"]["matched"] is True
    assert top["recommendation_reason"]


def test_shopping_guide_sku_comparison() -> None:
    payload = {
        "tenant_id": TENANT_ID,
        "session_id": "sg_test_compare_001",
        "user_no": "U100001",
        "message": "帮我对比一下 P100001 有哪些规格，哪个更适合我",
        "conversation_summary": "",
        "context": {
            "product_no": "P100001",
        },
    }

    data = _post_shopping_guide(payload)

    assert data["intent"] in {"shopping_guide", "sku_compare"}
    assert data["comparisons"], "comparisons should not be empty"

    comparison = data["comparisons"][0]
    assert comparison["product_no"] == "P100001"
    assert comparison["skus"]

    sku_nos = {sku["sku_no"] for sku in comparison["skus"]}
    assert "SKU100001" in sku_nos
    assert "SKU200001" not in sku_nos

    assert "规格" in data["answer"] or "SKU" in data["answer"] or "价格" in data["answer"]


def test_shopping_guide_uses_review_summary_for_reason() -> None:
    payload = {
        "tenant_id": TENANT_ID,
        "session_id": "sg_test_review_001",
        "user_no": "U100001",
        "message": "我想买评价好一点的商品，预算 300 以内",
        "conversation_summary": "",
        "context": {
            "budget_max": 300,
            "preferences": ["评价好"],
        },
    }

    data = _post_shopping_guide(payload)

    assert data["recommendations"]

    top = data["recommendations"][0]
    review_summary = top["review_summary"]

    assert review_summary
    assert "summary" in review_summary
    assert top["match_evidence"]["review_risk"]["reason"]
    assert top["recommendation_reason"]

    if review_summary["negative_count"] > 0:
        assert top["risk_notes"]


def test_shopping_guide_does_not_recommend_inactive_or_fake_products() -> None:
    payload = {
        "tenant_id": TENANT_ID,
        "session_id": "sg_test_active_filter_001",
        "user_no": "U100001",
        "message": "预算 300 以内，帮我推荐一个在售商品",
        "conversation_summary": "",
        "context": {
            "budget_max": 300,
        },
    }

    data = _post_shopping_guide(payload)

    _assert_recommendations_are_real_active_data(data)

    product_nos = {item["product_no"] for item in data["recommendations"]}
    assert "P100001" in product_nos
    assert "P200001" not in product_nos

    sku_nos = {
        sku["sku_no"]
        for item in data["recommendations"]
        for sku in item["matched_skus"]
    }

    assert "SKU100001" in sku_nos
    assert "SKU200001" not in sku_nos


def test_shopping_guide_multi_product_comparison() -> None:
    payload = {
        "tenant_id": TENANT_ID,
        "session_id": "sg_test_multi_compare_001",
        "user_no": "U100001",
        "message": "帮我对比几款在售商品，预算 1000 以内，看看哪个更适合办公室使用",
        "conversation_summary": "",
        "context": {
            "budget_max": 1000,
            "scenario": "office",
            "preferences": ["省心", "评价好"],
        },
    }

    data = _post_shopping_guide(payload)

    assert data["intent"] in {"shopping_guide", "sku_compare"}
    assert data["recommendations"]
    assert data["comparisons"]

    _assert_recommendations_are_real_active_data(data)

    # Demo 数据当前至少有 P100001 和 P200002 两个 active 商品。
    # 如果后续种子数据减少，这里会提醒总控同步测试数据。
    assert len(data["comparisons"]) >= 2

    required_dimension_names = {
        "价格",
        "场景匹配",
        "偏好匹配",
        "库存风险",
        "评价风险",
        "推荐理由",
    }

    for comparison in data["comparisons"]:
        assert comparison["product_no"]
        assert comparison["title"]
        assert comparison["skus"]
        assert comparison["recommendation_reason"]
        assert isinstance(comparison["total_score"], int)

        dimension_names = {
            dimension["name"]
            for dimension in comparison.get("dimensions", [])
        }

        assert required_dimension_names.issubset(dimension_names)

        for sku in comparison["skus"]:
            assert sku["status"] == "active"
            assert not sku["sku_no"].startswith("LLM_")
            assert not sku["sku_no"].startswith("MOCK_")


def test_shopping_guide_rag_knowledge_enrichment() -> None:
    payload = {
        "tenant_id": TENANT_ID,
        "session_id": "sg_test_rag_001",
        "user_no": "U100001",
        "message": "我预算 300 元以内，想买办公室用的小家电，选购时要注意什么？",
        "conversation_summary": "",
        "context": {
            "budget_max": 300,
            "scenario": "office",
            "preferences": ["安全", "省心"],
            "enable_knowledge": True,
        },
    }

    data = _post_shopping_guide(payload)

    assert data["recommendations"]
    _assert_recommendations_are_real_active_data(data)

    tool_names = {tool["tool_name"] for tool in data["tool_calls"]}
    assert "ask_shopping_knowledge" in tool_names

    metadata = data["metadata"]
    assert metadata["rag_boundary"]
    assert metadata["knowledge_boundary"]
    assert metadata["knowledge_used"] is True

    assert data["citations"], "RAG knowledge enrichment should return citations in current seeded environment"

    # RAG 只能增强解释，不能污染商品结构。
    product_nos = {item["product_no"] for item in data["recommendations"]}
    assert "P100001" in product_nos
    assert "P200001" not in product_nos

    sku_nos = {
        sku["sku_no"]
        for item in data["recommendations"]
        for sku in item["matched_skus"]
    }
    assert "SKU100001" in sku_nos
    assert "SKU200001" not in sku_nos

    # mock RAG 输出不能把 Prompt 原文直接拼到 answer。
    assert "[mock]" not in data["answer"]
    assert "你是企业知识库问答助手" not in data["answer"]
    assert "回答规则" not in data["answer"]

    for citation in data["citations"]:
        assert citation["document_id"]
        assert citation["document_title"]
        assert citation["chunk_id"]
        assert citation["content_snippet"]


def test_shopping_guide_score_breakdown_drives_recommendation_reason() -> None:
    payload = {
        "tenant_id": TENANT_ID,
        "session_id": "sg_test_score_001",
        "user_no": "U100001",
        "message": "预算 300 元以内，帮我推荐一个适合办公室、安全省心的商品",
        "conversation_summary": "",
        "context": {
            "budget_max": 300,
            "scenario": "office",
            "preferences": ["安全", "省心"],
        },
    }

    data = _post_shopping_guide(payload)

    assert data["recommendations"]

    top = data["recommendations"][0]
    _assert_match_evidence(top)

    score_breakdown = top["score_breakdown"]

    assert score_breakdown["total_score"] > 0
    assert "综合推荐分" in top["recommendation_reason"]

    # 推荐理由必须能追溯到 score_breakdown 和 match_evidence。
    assert score_breakdown["budget_score"]["reason"] in top["recommendation_reason"]
    assert score_breakdown["stock_score"]["reason"] in top["recommendation_reason"]
    assert score_breakdown["review_score"]["reason"] in top["recommendation_reason"]
