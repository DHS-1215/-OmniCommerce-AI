# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/05/03 14:28
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
SHOPPING_GUIDE_INTENT = "shopping_guide"
SKU_COMPARE_INTENT = "sku_compare"
GENERAL_SHOPPING_INTENT = "general_shopping"


def detect_shopping_intent(message: str, context: dict | None = None) -> str:
    context = context or {}

    if context.get("product_no") or context.get("sku_no"):
        return SKU_COMPARE_INTENT

    compare_keywords = ["对比", "比较", "哪个", "规格", "SKU", "sku"]
    if any(keyword in message for keyword in compare_keywords):
        return SKU_COMPARE_INTENT

    shopping_keywords = [
        "推荐",
        "买",
        "选",
        "预算",
        "适合",
        "导购",
        "哪个好",
        "性价比",
        "办公室",
        "家用",
        "宿舍",
    ]
    if any(keyword in message for keyword in shopping_keywords):
        return SHOPPING_GUIDE_INTENT

    return GENERAL_SHOPPING_INTENT
