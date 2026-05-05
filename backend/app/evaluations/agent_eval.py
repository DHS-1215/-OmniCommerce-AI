# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/05/04 15:39
IDE       :PyCharm
作者      :董宏升
Agent 评测执行器。
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
import time
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.customer_service.service import CustomerServiceAgentService
from app.agents.operation_copilot.service import OperationCopilotAgentService
from app.agents.shopping_guide.service import ShoppingGuideAgentService
from app.evaluations.metrics import EvaluationMetricCalculator
from app.models.evaluation import EvaluationCase
from app.schemas.agent import CustomerServiceChatRequest
from app.schemas.operation_copilot import OperationCopilotChatRequest
from app.schemas.shopping_guide import ShoppingGuideChatRequest


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


class AgentEvaluator:
    """执行 Agent 用例并计算指标。"""

    def __init__(self) -> None:
        self.metric_calculator = EvaluationMetricCalculator()

    async def run_case(
            self,
            db: AsyncSession,
            *,
            case: EvaluationCase,
            tenant_id: UUID,
            agent_type: str,
            request_id: str | None = None,
    ) -> tuple[dict[str, Any] | None, dict[str, Any], int, str | None]:
        """
        执行单条 Agent 用例。

        agent_type 支持：
        - customer_service
        - shopping_guide
        - operation_copilot
        """

        input_json = case.input_json or {}
        effective_agent_type = (
                input_json.get("agent_type")
                or (case.metadata_json or {}).get("agent_type")
                or agent_type
        )

        message = str(
            input_json.get("message")
            or input_json.get("question")
            or input_json.get("query")
            or ""
        )

        if not message:
            return None, {}, 0, "Agent 评测用例缺少 message/question/query"

        session_id = str(input_json.get("session_id") or f"eval_{case.case_no}")
        user_no = input_json.get("user_no")
        conversation_summary = input_json.get("conversation_summary") or ""
        context = input_json.get("context") or {}

        started_at = time.perf_counter()

        if effective_agent_type == "customer_service":
            service = CustomerServiceAgentService(db)
            payload = CustomerServiceChatRequest(
                tenant_id=tenant_id,
                session_id=session_id,
                user_no=user_no,
                user_id=input_json.get("user_id"),
                message=message,
                conversation_summary=conversation_summary,
                context=context,
            )
            response = await service.chat(request=payload, request_id=request_id)

        elif effective_agent_type == "shopping_guide":
            service = ShoppingGuideAgentService(db)
            payload = ShoppingGuideChatRequest(
                tenant_id=tenant_id,
                session_id=session_id,
                user_no=user_no,
                message=message,
                conversation_summary=conversation_summary,
                context=context,
            )
            response = await service.chat(request=payload, request_id=request_id)

        elif effective_agent_type == "operation_copilot":
            service = OperationCopilotAgentService(db)
            payload = OperationCopilotChatRequest(
                tenant_id=tenant_id,
                session_id=session_id,
                user_no=user_no,
                message=message,
                conversation_summary=conversation_summary,
                context=context,
            )
            response = await service.chat(request=payload, request_id=request_id)

        else:
            return None, {}, 0, f"不支持的 Agent 类型：{effective_agent_type}"

        latency_ms = int((time.perf_counter() - started_at) * 1000)
        response_data = _model_to_jsonable(response)

        metrics = self.metric_calculator.evaluate_agent(
            response_data=response_data,
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
            "tool_call_success_rate": (
                float(metrics.tool_call_success_rate)
                if metrics.tool_call_success_rate is not None
                else None
            ),
            "agent_task_success_rate": (
                float(metrics.agent_task_success_rate)
                if metrics.agent_task_success_rate is not None
                else None
            ),
            "agent_type": effective_agent_type,
        }

        return response_data, metric_values, latency_ms, None
