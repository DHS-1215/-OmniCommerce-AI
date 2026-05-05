# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any


def detect_operation_intent(message: str, context: dict[str, Any] | None = None) -> str:
    context = context or {}
    requested_intent = context.get("intent")
    if requested_intent:
        return str(requested_intent)

    text = (message or "").lower()

    metric_keywords = [
        "sql",
        "查询",
        "指标",
        "gmv",
        "库存",
        "转化率",
        "转化",
        "客单价",
        "订单",
        "订单数",
        "销售额",
        "成交额",
        "实付金额",
        "退款",
        "售后",
        "评价",
        "评论",
        "好评",
        "差评",
    ]

    explicit_report_keywords = ["复盘", "报告", "总结", "经营分析"]

    # 明确要求“报告/复盘/总结”时，进入报告流程。
    # 但“分析一下转化率”这种只有分析动词 + 指标词的请求，仍然是指标查询。
    if any(keyword in text for keyword in explicit_report_keywords):
        return "operation_report"

    if any(keyword in text for keyword in metric_keywords):
        return "metric_query"

    if "分析一下" in text:
        return "operation_report"

    return "metric_query"


def extract_metric_keys(message: str, context: dict[str, Any] | None = None) -> list[str]:
    context = context or {}

    explicit = context.get("metric_keys")
    if isinstance(explicit, list) and explicit:
        return [str(item) for item in explicit]

    metric_key = context.get("metric_key")
    if metric_key:
        return [str(metric_key)]

    text = (message or "").lower()
    keys: list[str] = []

    if "gmv" in text or "销售额" in text or "成交额" in text or "实付金额" in text:
        keys.append("gmv")

    if "订单数" in text or "多少单" in text:
        keys.append("order_count")

    if "客单价" in text:
        keys.append("avg_order_value")

    if "低库存" in text:
        keys.append("low_stock_sku_count")

    if "库存" in text and "low_stock_sku_count" not in keys:
        keys.append("inventory_stock")

    if "转化率" in text or "转化" in text:
        keys.append("conversion_rate")

    if "退款金额" in text:
        keys.append("refund_amount")

    if "售后" in text and "after_sale_count" not in keys:
        keys.append("after_sale_count")

    if "评价" in text or "评论" in text:
        keys.append("review_count")

    if "好评" in text or "正向评价" in text:
        keys.append("positive_review_count")

    if "差评" in text or "负向评价" in text:
        keys.append("negative_review_count")

    if not keys:
        keys = ["gmv", "order_count"]

    deduped: list[str] = []
    for key in keys:
        if key not in deduped:
            deduped.append(key)

    return deduped