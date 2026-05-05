# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/05/04 15:25
IDE       :PyCharm
作者      :董宏升

执行窗口 11：评测指标计算。

第一版采用确定性、可复现的自定义评测逻辑，避免评测测试依赖真实模型 API。
后续如接入 Ragas，可在不改变 evaluation_result 入库合同的前提下替换或增强这些指标。
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
import re
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Any


def clamp_score(value: float | None) -> float | None:
    """将分数限制在 0 到 1 之间。"""

    if value is None:
        return None
    return max(0.0, min(1.0, float(value)))


def to_decimal_score(value: float | None) -> Decimal | None:
    """转换为 evaluation_result 表可保存的 Decimal 分数。"""

    value = clamp_score(value)
    if value is None:
        return None
    return Decimal(str(value)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def flatten_text(value: Any) -> str:
    """把 dict/list/标量压平成可做轻量文本匹配的字符串。"""

    if value is None:
        return ""

    if isinstance(value, str):
        return value

    if isinstance(value, (int, float, bool)):
        return str(value)

    if isinstance(value, dict):
        parts: list[str] = []
        for key, item in value.items():
            parts.append(str(key))
            parts.append(flat_text := flatten_text(item))
        return "\n".join(part for part in parts if part)

    if isinstance(value, list):
        return "\n".join(flatten_text(item) for item in value)

    return str(value)


_WORD_RE = re.compile(r"[a-zA-Z0-9_]+|[\u4e00-\u9fff]")


def tokenize(text: str) -> set[str]:
    """
    中英文混合轻量分词。

    英文按单词切，中文按单字切。
    这不是最终的语义评测模型，但优点是稳定、可复现、测试不依赖外部 API。
    """

    if not text:
        return set()
    return {item.lower() for item in _WORD_RE.findall(text)}


def overlap_ratio(*, expected: str, actual: str) -> float | None:
    """召回式重合率：期望内容中有多少被实际内容覆盖。"""

    expected_tokens = tokenize(expected)
    actual_tokens = tokenize(actual)

    if not expected_tokens:
        return None

    if not actual_tokens:
        return 0.0

    return len(expected_tokens & actual_tokens) / len(expected_tokens)


def precision_ratio(*, reference: str, actual: str) -> float | None:
    """精确式重合率：实际内容有多少能被参考内容支撑。"""

    reference_tokens = tokenize(reference)
    actual_tokens = tokenize(actual)

    if not actual_tokens:
        return 0.0

    if not reference_tokens:
        return None

    return len(reference_tokens & actual_tokens) / len(actual_tokens)


def extract_ids(items: list[Any] | None, *, id_keys: tuple[str, ...]) -> set[str]:
    """从 citations / reference_context 中提取 document_id / chunk_id 等标识。"""

    values: set[str] = set()

    for item in items or []:
        if not isinstance(item, dict):
            continue

        for key in id_keys:
            value = item.get(key)
            if value is not None:
                values.add(str(value))

    return values


def average_non_null(values: list[float | None]) -> float | None:
    """计算非空分数均值。"""

    valid = [clamp_score(item) for item in values if item is not None]
    valid = [item for item in valid if item is not None]

    if not valid:
        return None

    return sum(valid) / len(valid)


@dataclass(slots=True)
class MetricBundle:
    """评测指标集合。"""

    score: float | None = None
    answer_relevance: float | None = None
    faithfulness: float | None = None
    context_recall: float | None = None
    context_precision: float | None = None
    tool_call_success_rate: float | None = None
    agent_task_success_rate: float | None = None

    def to_decimal_dict(self) -> dict[str, Decimal | None]:
        """转换成 evaluation_result 入库字段。"""

        return {
            "score": to_decimal_score(self.score),
            "answer_relevance": to_decimal_score(self.answer_relevance),
            "faithfulness": to_decimal_score(self.faithfulness),
            "context_recall": to_decimal_score(self.context_recall),
            "context_precision": to_decimal_score(self.context_precision),
            "tool_call_success_rate": to_decimal_score(self.tool_call_success_rate),
            "agent_task_success_rate": to_decimal_score(self.agent_task_success_rate),
        }


class EvaluationMetricCalculator:
    """评测指标计算器。"""

    def evaluate_rag(
            self,
            *,
            question: str,
            answer: str,
            citations: list[dict[str, Any]],
            expected_output: dict[str, Any] | None,
            reference_context: list[Any] | None,
    ) -> MetricBundle:
        """
        计算 RAG 评测指标。

        第一版指标：
        - answer_relevance：答案和期望输出 / 问题的重合度
        - faithfulness：答案是否能被引用上下文支撑
        - context_recall：引用是否覆盖参考上下文
        - context_precision：引用是否和问题 / 参考上下文相关
        """

        expected_text = flatten_text(expected_output)
        context_text = flatten_text(reference_context) or flatten_text(citations)

        answer_relevance = overlap_ratio(
            expected=expected_text or question,
            actual=answer,
        )
        faithfulness = precision_ratio(
            reference=context_text,
            actual=answer,
        )
        context_recall = self._context_recall(
            citations=citations,
            reference_context=reference_context,
        )
        context_precision = self._context_precision(
            question=question,
            citations=citations,
            reference_context=reference_context,
        )

        score = average_non_null([
            answer_relevance,
            faithfulness,
            context_recall,
            context_precision,
        ])

        return MetricBundle(
            score=score,
            answer_relevance=answer_relevance,
            faithfulness=faithfulness,
            context_recall=context_recall,
            context_precision=context_precision,
        )

    def evaluate_agent(
            self,
            *,
            response_data: dict[str, Any],
            expected_output: dict[str, Any] | None,
            reference_context: list[Any] | None = None,
    ) -> MetricBundle:
        """
        计算 Agent 评测指标。

        第一版重点评估：
        - 意图是否符合预期
        - 是否按预期转人工
        - 工具是否调用成功
        - 是否调用了必须工具 / 避免了禁止工具
        - RAG Agent 场景下 citations 是否可靠
        """

        expected_output = expected_output or {}

        answer = str(response_data.get("answer") or "")
        expected_answer_text = flatten_text(expected_output.get("answer") or expected_output)

        answer_relevance = overlap_ratio(
            expected=expected_answer_text or str(response_data.get("intent") or ""),
            actual=answer,
        )

        tool_call_success_rate = self._tool_call_success_rate(
            response_data.get("tool_calls") or [],
        )
        agent_task_success_rate = self._agent_task_success_rate(
            response_data=response_data,
            expected_output=expected_output,
        )

        citations = response_data.get("citations") or []
        context_recall = None
        context_precision = None
        faithfulness = None

        if citations or reference_context:
            faithfulness = precision_ratio(
                reference=flatten_text(reference_context) or flatten_text(citations),
                actual=answer,
            )
            context_recall = self._context_recall(
                citations=citations,
                reference_context=reference_context,
            )
            context_precision = self._context_precision(
                question=str(expected_output.get("question") or ""),
                citations=citations,
                reference_context=reference_context,
            )

        score = average_non_null([
            answer_relevance,
            tool_call_success_rate,
            agent_task_success_rate,
            faithfulness,
            context_recall,
            context_precision,
        ])

        return MetricBundle(
            score=score,
            answer_relevance=answer_relevance,
            faithfulness=faithfulness,
            context_recall=context_recall,
            context_precision=context_precision,
            tool_call_success_rate=tool_call_success_rate,
            agent_task_success_rate=agent_task_success_rate,
        )

    def _context_recall(
            self,
            *,
            citations: list[dict[str, Any]],
            reference_context: list[Any] | None,
    ) -> float | None:
        """计算上下文召回率。"""

        if not reference_context:
            return 1.0 if citations else 0.0

        expected_ids = extract_ids(
            reference_context,
            id_keys=("chunk_id", "document_id", "id"),
        )
        actual_ids = extract_ids(
            citations,
            id_keys=("chunk_id", "document_id", "id"),
        )

        if expected_ids:
            return len(expected_ids & actual_ids) / len(expected_ids)

        return overlap_ratio(
            expected=flatten_text(reference_context),
            actual=flatten_text(citations),
        )

    def _context_precision(
            self,
            *,
            question: str,
            citations: list[dict[str, Any]],
            reference_context: list[Any] | None,
    ) -> float | None:
        """计算上下文精确率。"""

        if not citations:
            return 0.0

        reference_text = flatten_text(reference_context) or question
        if not reference_text:
            return None

        hits = 0
        for citation in citations:
            score = precision_ratio(
                reference=reference_text,
                actual=flatten_text(citation),
            )
            if score is not None and score > 0:
                hits += 1

        return hits / len(citations)

    @staticmethod
    def _tool_call_success_rate(tool_calls: list[Any]) -> float | None:
        """计算工具调用成功率。"""

        if not tool_calls:
            return None

        total = 0
        success = 0

        for item in tool_calls:
            if not isinstance(item, dict):
                continue

            total += 1
            if bool(item.get("success")) or item.get("status") == "success":
                success += 1

        if total == 0:
            return None

        return success / total

    @staticmethod
    def _agent_task_success_rate(
            *,
            response_data: dict[str, Any],
            expected_output: dict[str, Any],
    ) -> float:
        """基于结构化期望判断 Agent 任务成功率。"""

        checks: list[bool] = []

        expected_intent = expected_output.get("intent")
        if expected_intent is not None:
            checks.append(str(response_data.get("intent")) == str(expected_intent))

        if "handoff_required" in expected_output:
            checks.append(
                bool(response_data.get("handoff_required"))
                is bool(expected_output.get("handoff_required"))
            )

        expected_tools = (
                expected_output.get("expected_tools")
                or expected_output.get("tool_names")
                or []
        )
        if expected_tools:
            actual_tools = {
                str(item.get("tool_name"))
                for item in response_data.get("tool_calls") or []
                if isinstance(item, dict)
            }
            checks.append(set(map(str, expected_tools)).issubset(actual_tools))

        forbidden_tools = expected_output.get("forbidden_tools") or []
        if forbidden_tools:
            actual_tools = {
                str(item.get("tool_name"))
                for item in response_data.get("tool_calls") or []
                if isinstance(item, dict)
            }
            checks.append(actual_tools.isdisjoint(set(map(str, forbidden_tools))))

        if not checks:
            # 没有显式期望时，只要 Agent 给出 answer 且没有 error，就认为任务主流程成功。
            return 1.0 if response_data.get("answer") and not response_data.get("error_code") else 0.0

        return sum(1 for item in checks if item) / len(checks)
