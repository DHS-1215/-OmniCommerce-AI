# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/05/02 20:22
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from enum import StrEnum


class CustomerServiceIntent(StrEnum):
    """智能客服意图枚举。"""

    PRODUCT_QUERY = "product_query"
    ORDER_QUERY = "order_query"
    AFTERSALE_APPLY = "aftersale_apply"
    AFTERSALE_QUERY = "aftersale_query"
    POLICY_QUERY = "policy_query"
    COMPLAINT = "complaint"
    HUMAN_HANDOFF = "human_handoff"
    GENERAL_CHAT = "general_chat"
    UNKNOWN = "unknown"


INTENT_LABELS: dict[str, str] = {
    CustomerServiceIntent.PRODUCT_QUERY: "商品咨询",
    CustomerServiceIntent.ORDER_QUERY: "订单查询",
    CustomerServiceIntent.AFTERSALE_APPLY: "售后申请",
    CustomerServiceIntent.AFTERSALE_QUERY: "售后进度查询",
    CustomerServiceIntent.POLICY_QUERY: "政策问答",
    CustomerServiceIntent.COMPLAINT: "投诉",
    CustomerServiceIntent.HUMAN_HANDOFF: "人工转接",
    CustomerServiceIntent.GENERAL_CHAT: "普通咨询",
    CustomerServiceIntent.UNKNOWN: "未知意图",
}


def normalize_intent(value: str | None) -> CustomerServiceIntent:
    """将模型输出或规则识别结果归一化为客服意图。"""

    if not value:
        return CustomerServiceIntent.UNKNOWN

    normalized = value.strip().lower()

    for intent in CustomerServiceIntent:
        if normalized == intent.value:
            return intent

    # 兼容模型输出中文标签的情况。
    reverse_labels = {label: intent for intent, label in INTENT_LABELS.items()}
    if value.strip() in reverse_labels:
        return CustomerServiceIntent(reverse_labels[value.strip()])

    return CustomerServiceIntent.UNKNOWN
