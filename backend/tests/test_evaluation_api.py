# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/05/04 17:22
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
import os
from uuid import uuid4

import httpx

BASE_URL = os.getenv("TEST_API_BASE_URL", os.getenv("API_BASE_URL", "http://127.0.0.1:8000"))
TENANT_ID = "00000000-0000-0000-0000-000000000001"


def _client() -> httpx.Client:
    return httpx.Client(base_url=BASE_URL, timeout=60.0, trust_env=False)


def _post(path: str, payload: dict) -> dict:
    with _client() as client:
        response = client.post(path, json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True
    assert body["code"] == "OK"
    assert body["request_id"] is not None
    return body["data"]


def _get(path: str, *, params: dict) -> dict:
    with _client() as client:
        response = client.get(path, params=params)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True
    assert body["code"] == "OK"
    assert body["request_id"] is not None
    return body["data"]


def test_evaluation_case_crud_and_agent_run() -> None:
    suffix = uuid4().hex[:8]
    case_no = f"EVAL_CS_ORDER_{suffix}"
    run_no = f"EVAL_RUN_{suffix}"

    created = _post(
        "/api/v1/evaluations/cases",
        {
            "tenant_id": TENANT_ID,
            "case_no": case_no,
            "case_type": "customer_service_agent",
            "name": "客服订单查询评测用例",
            "description": "验证客服 Agent 能识别订单查询并调用订单详情工具",
            "input_json": {
                "session_id": f"eval_session_{suffix}",
                "user_no": "U100001",
                "message": "我的订单 O100001 到哪了？",
                "conversation_summary": "",
                "context": {
                    "order_no": "O100001",
                },
            },
            "expected_output_json": {
                "intent": "order_query",
                "handoff_required": False,
                "expected_tools": [
                    "get_order_detail",
                ],
                "answer": "订单 O100001 已送达",
            },
            "reference_context_json": [],
            "tags_json": [
                "customer_service",
                "order",
            ],
            "metadata_json": {
                "created_by": "test_evaluation_api",
            },
        },
    )

    assert created["case_no"] == case_no
    assert created["case_type"] == "customer_service_agent"
    assert created["status"] == "active"
    case_id = created["id"]

    cases = _get(
        "/api/v1/evaluations/cases",
        params={
            "tenant_id": TENANT_ID,
            "case_type": "customer_service_agent",
            "keyword": case_no,
            "page": 1,
            "page_size": 10,
        },
    )

    assert cases["total"] >= 1
    assert any(item["case_no"] == case_no for item in cases["items"])

    run_result = _post(
        "/api/v1/evaluations/agents/run",
        {
            "tenant_id": TENANT_ID,
            "agent_type": "customer_service",
            "case_ids": [
                case_id,
            ],
            "run_no": run_no,
            "target_id": "customer_service_agent_v1",
            "metadata_json": {
                "test": True,
            },
        },
    )

    assert run_result["run_no"] == run_no
    assert run_result["target_type"] == "customer_service_agent"
    assert run_result["total"] == 1
    assert run_result["success_count"] == 1
    assert run_result["failed_count"] == 0

    result = run_result["results"][0]
    assert result["case_id"] == case_id
    assert result["status"] == "success"
    assert result["target_type"] == "customer_service_agent"
    assert result["target_id"] == "customer_service_agent_v1"
    assert result["score"] is not None
    assert result["tool_call_success_rate"] == "1.0000"
    assert result["agent_task_success_rate"] == "1.0000"

    results = _get(
        "/api/v1/evaluations/results",
        params={
            "tenant_id": TENANT_ID,
            "run_no": run_no,
            "page": 1,
            "page_size": 10,
        },
    )

    assert results["total"] >= 1
    assert any(item["case_id"] == case_id for item in results["items"])

    report = _get(
        "/api/v1/evaluations/report",
        params={
            "tenant_id": TENANT_ID,
            "run_no": run_no,
            "target_type": "customer_service_agent",
        },
    )

    assert report["run_no"] == run_no
    assert report["target_type"] == "customer_service_agent"
    assert report["total"] >= 1
    assert report["success_count"] >= 1
    assert report["avg_score"] is not None


def test_evaluation_rag_run_should_persist_result_even_when_retrieval_fails() -> None:
    suffix = uuid4().hex[:8]
    case_no = f"EVAL_RAG_POLICY_{suffix}"
    run_no = f"EVAL_RAG_RUN_{suffix}"

    created = _post(
        "/api/v1/evaluations/cases",
        {
            "tenant_id": TENANT_ID,
            "case_no": case_no,
            "case_type": "rag",
            "name": "RAG 政策问答评测用例",
            "description": "验证 RAG 评测链路会写入 evaluation_result",
            "status": "inactive",
            "input_json": {
                "question": "七天无理由退货需要满足什么条件？",
                "top_k": 5,
            },
            "expected_output_json": {
                "answer": (
                    "七天无理由退货需要满足：商品未拆封、不影响二次销售，"
                    "并且用户在签收后 7 天内提交申请。"
                    "定制商品、已拆封耳机、影响二次销售的商品不支持七天无理由退货。"
                ),
            },
            "reference_context_json": [
                {
                    "content": (
                        "智营商城支持七天无理由退货。"
                        "退货条件：1. 商品未拆封；"
                        "2. 不影响二次销售；"
                        "3. 用户需要在签收后 7 天内提交申请。"
                        "退款将在审核通过后 3 个工作日内原路退回。"
                        "特殊说明：定制商品、已拆封耳机、影响二次销售的商品不支持七天无理由退货。"
                    ),
                }
            ],
            "metadata_json": {
                "expected_keywords": [
                    "商品未拆封",
                    "不影响二次销售",
                    "签收后 7 天内",
                    "提交申请",
                    "定制商品",
                    "已拆封耳机",
                    "不支持七天无理由退货",
                ],
            },
            "tags_json": [
                "rag",
                "policy",
            ],
        },
    )

    run_result = _post(
        "/api/v1/evaluations/rag/run",
        {
            "tenant_id": TENANT_ID,
            "case_ids": [
                created["id"],
            ],
            "run_no": run_no,
            "target_id": "hybrid_opensearch_default",
            "top_k": 5,
            "metadata_json": {
                "strategy_id": "hybrid_opensearch_default",
            },
        },
    )

    assert run_result["run_no"] == run_no
    assert run_result["target_type"] == "rag"
    assert run_result["total"] == 1

    # 本测试关注“结果必须入库”。如果本地知识库未初始化，允许该条为 failed。
    result = run_result["results"][0]
    assert result["case_id"] == created["id"]
    assert result["target_type"] == "rag"
    assert result["target_id"] == "hybrid_opensearch_default"
    assert result["status"] in {"success", "failed"}

    results = _get(
        "/api/v1/evaluations/results",
        params={
            "tenant_id": TENANT_ID,
            "run_no": run_no,
            "target_type": "rag",
            "page": 1,
            "page_size": 10,
        },
    )

    assert results["total"] >= 1


def test_evaluation_compare_endpoints_should_return_structured_data() -> None:
    suffix = uuid4().hex[:8]

    prompt_compare = _post(
        "/api/v1/evaluations/compare/prompts",
        {
            "tenant_id": TENANT_ID,
            "prompt_version_ids": [
                str(uuid4()),
                str(uuid4()),
            ],
            "run_no": f"NO_EXIST_PROMPT_COMPARE_{suffix}",
            "metadata_json": {
                "test": True,
            },
        },
    )

    assert prompt_compare["target_type"] == "prompt"
    assert len(prompt_compare["items"]) == 2

    retrieval_compare = _post(
        "/api/v1/evaluations/compare/retrieval",
        {
            "tenant_id": TENANT_ID,
            "strategies": [
                {
                    "strategy_id": "hybrid_default",
                    "vector_weight": 0.65,
                    "keyword_weight": 0.35,
                    "top_k": 5,
                },
                {
                    "strategy_id": "keyword_heavy",
                    "vector_weight": 0.35,
                    "keyword_weight": 0.65,
                    "top_k": 5,
                },
            ],
            "run_no": f"NO_EXIST_RETRIEVAL_COMPARE_{suffix}",
            "metadata_json": {
                "test": True,
            },
        },
    )

    assert retrieval_compare["target_type"] == "rag"
    assert len(retrieval_compare["items"]) == 2
    assert "strategies" in retrieval_compare
