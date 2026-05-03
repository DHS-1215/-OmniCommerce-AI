# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/05/02 20:34
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from decimal import Decimal
from typing import Any

from app.agents.customer_service.intents import CustomerServiceIntent

LOW_CONFIDENCE_THRESHOLD = 0.6
LARGE_ORDER_AMOUNT_THRESHOLD = Decimal("1000.00")

HIGH_RISK_KEYWORDS = [
    "投诉",
    "赔偿",
    "赔付",
    "退款争议",
    "威胁",
    "曝光",
    "报警",
    "律师",
    "315",
    "消协",
    "欺诈",
    "虚假宣传",
    "平台责任",
]

HUMAN_HANDOFF_KEYWORDS = [
    "人工",
    "真人",
    "客服经理",
    "转人工",
    "人工客服",
    "找人处理",
    "别让机器人",
]


def contains_any_keyword(text: str | None, keywords: list[str]) -> bool:
    if not text:
        return False

    lowered = text.lower()
    return any(keyword.lower() in lowered for keyword in keywords)


def is_human_handoff_requested(message: str | None) -> bool:
    """用户是否明确要求人工客服。"""

    return contains_any_keyword(message, HUMAN_HANDOFF_KEYWORDS)


def is_high_risk_message(message: str | None) -> bool:
    """用户输入是否包含高风险表达。"""

    return contains_any_keyword(message, HIGH_RISK_KEYWORDS)


def is_low_confidence(confidence: float | None) -> bool:
    """模型意图识别置信度是否过低。"""

    if confidence is None:
        return True
    return confidence < LOW_CONFIDENCE_THRESHOLD


def is_tool_failure(tool_results: list[dict[str, Any]] | None) -> bool:
    """是否存在工具调用失败。"""

    if not tool_results:
        return False

    return any(result.get("success") is False for result in tool_results)


def is_policy_uncertain(intent: str | None, citations: list[dict[str, Any]] | None) -> bool:
    """政策类问题没有引用来源时，视为政策不确定。"""

    if intent != CustomerServiceIntent.POLICY_QUERY:
        return False

    return not citations


def should_handoff(
        *,
        message: str | None,
        intent: str | None,
        confidence: float | None = None,
        tool_results: list[dict[str, Any]] | None = None,
        citations: list[dict[str, Any]] | None = None,
) -> tuple[bool, str | None]:
    """判断是否需要转人工。

    返回：
    - 是否转人工；
    - 转人工原因。
    """

    if is_human_handoff_requested(message):
        return True, "用户明确要求人工客服"

    if is_high_risk_message(message):
        return True, "用户表达涉及投诉、赔付、曝光等高风险诉求"

    if intent in {
        CustomerServiceIntent.COMPLAINT,
        CustomerServiceIntent.HUMAN_HANDOFF,
    }:
        return True, "识别为投诉或人工转接意图"

    if is_low_confidence(confidence):
        return True, "意图识别置信度过低"

    if is_tool_failure(tool_results):
        return True, "工具调用失败，需要人工介入"

    if is_policy_uncertain(intent, citations):
        return True, "政策类问题未检索到可靠引用来源"

    return False, None
