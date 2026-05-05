# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/05/04 15:27
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from app.evaluations.metrics import EvaluationMetricCalculator, tokenize


def test_tokenize_should_support_chinese_and_english() -> None:
    tokens = tokenize("七天无理由 return policy")

    assert "七" in tokens
    assert "return" in tokens
    assert "policy" in tokens


def test_rag_metrics_should_calculate_relevance_and_context_scores() -> None:
    calculator = EvaluationMetricCalculator()

    metrics = calculator.evaluate_rag(
        question="七天无理由退货条件是什么？",
        answer="七天无理由退货需要商品完好，并保留完整包装。",
        citations=[
            {
                "document_id": "doc1",
                "chunk_id": "chunk1",
                "content_snippet": "七天无理由退货需要商品完好，包装完整。",
            }
        ],
        expected_output={"answer": "商品完好，包装完整"},
        reference_context=[
            {
                "document_id": "doc1",
                "chunk_id": "chunk1",
                "content": "七天无理由退货需要商品完好，包装完整。",
            }
        ],
    )

    assert metrics.answer_relevance is not None
    assert metrics.answer_relevance > 0
    assert metrics.context_recall == 1.0
    assert metrics.context_precision == 1.0
    assert metrics.score is not None
    assert 0 <= metrics.score <= 1


def test_agent_metrics_should_check_intent_tools_and_handoff() -> None:
    calculator = EvaluationMetricCalculator()

    metrics = calculator.evaluate_agent(
        response_data={
            "intent": "complaint",
            "answer": "已经为你转人工处理。",
            "handoff_required": True,
            "tool_calls": [
                {
                    "tool_name": "create_customer_service_ticket",
                    "success": True,
                },
            ],
        },
        expected_output={
            "intent": "complaint",
            "handoff_required": True,
            "expected_tools": ["create_customer_service_ticket"],
        },
    )

    assert metrics.tool_call_success_rate == 1.0
    assert metrics.agent_task_success_rate == 1.0
    assert metrics.score is not None
    assert metrics.score > 0


def test_agent_metrics_should_detect_forbidden_tool() -> None:
    calculator = EvaluationMetricCalculator()

    metrics = calculator.evaluate_agent(
        response_data={
            "intent": "complaint",
            "answer": "已经为你转人工处理。",
            "handoff_required": True,
            "tool_calls": [
                {
                    "tool_name": "list_orders",
                    "success": True,
                },
            ],
        },
        expected_output={
            "intent": "complaint",
            "handoff_required": True,
            "forbidden_tools": ["list_orders"],
        },
    )

    assert metrics.agent_task_success_rate < 1.0
