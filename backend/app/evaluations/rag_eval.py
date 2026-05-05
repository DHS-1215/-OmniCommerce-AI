# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/05/04 15:38
IDE       :PyCharm
作者      :董宏升
RAG 评测执行器。
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
import time
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.evaluations.metrics import EvaluationMetricCalculator
from app.models.evaluation import EvaluationCase
from app.services.knowledge_service import KnowledgeService


def _model_to_jsonable(value: Any) -> Any:
    if value is None:
        return None

    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")

    if isinstance(value, list):
        return [_model_to_jsonable(item) for item in value]

    if isinstance(value, tuple):
        return [_model_to_jsonable(item) for item in value]

    if isinstance(value, dict):
        return {key: _model_to_jsonable(item) for key, item in value.items()}

    return value


class RagEvaluator:
    """执行 RAG 用例并计算指标。"""

    def __init__(self) -> None:
        self.knowledge_service = KnowledgeService()
        self.metric_calculator = EvaluationMetricCalculator()

    async def run_case(
            self,
            db: AsyncSession,
            *,
            case: EvaluationCase,
            tenant_id: UUID,
            top_k: int | None = None,
            request_id: str | None = None,
    ) -> tuple[dict[str, Any] | None, dict[str, Any], int, str | None]:
        """
        执行单条 RAG 用例。

        返回：
        - response_data：RAG 响应 JSON
        - metric_values：可入库的 Decimal 指标 dict
        - latency_ms：耗时
        - error_message：单条失败原因
        """

        input_json = case.input_json or {}
        question = (
                input_json.get("question")
                or input_json.get("query")
                or input_json.get("message")
        )

        if not question:
            return None, {}, 0, "RAG 评测用例缺少 question/query/message"

        started_at = time.perf_counter()

        response = await self.knowledge_service.ask(
            db,
            tenant_id=tenant_id,
            question=str(question),
            top_k=top_k or input_json.get("top_k"),
            request_id=request_id,
            user_id=input_json.get("user_id"),
        )

        latency_ms = int((time.perf_counter() - started_at) * 1000)
        response_data = _model_to_jsonable(response)

        citations = response_data.get("citations") or []
        metrics = self.metric_calculator.evaluate_rag(
            question=str(question),
            answer=str(response_data.get("answer") or ""),
            citations=citations,
            expected_output=case.expected_output_json,
            reference_context=case.reference_context_json,
        )

        metric_values = metrics.to_decimal_dict()
        metric_values["metrics_json"] = {
            "score": float(metrics.score) if metrics.score is not None else None,
            "answer_relevance": (
                float(metrics.answer_relevance)
                if metrics.answer_relevance is not None
                else None
            ),
            "faithfulness": (
                float(metrics.faithfulness)
                if metrics.faithfulness is not None
                else None
            ),
            "context_recall": (
                float(metrics.context_recall)
                if metrics.context_recall is not None
                else None
            ),
            "context_precision": (
                float(metrics.context_precision)
                if metrics.context_precision is not None
                else None
            ),
            "citation_count": len(citations),
        }

        return response_data, metric_values, latency_ms, None
