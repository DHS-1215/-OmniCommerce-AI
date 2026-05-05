# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/05/03 14:29
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from typing import Any, TypedDict
from uuid import UUID


class ShoppingGuideState(TypedDict, total=False):
    tenant_id: UUID
    user_no: str | None
    session_id: str
    request_id: str | None
    message: str
    conversation_summary: str | None
    context: dict[str, Any]

    agent_task_id: UUID | None
    agent_task_no: str | None

    intent: str
    parsed_need: dict[str, Any]
    budget: dict[str, Any] | None
    scenario: str | None
    preferences: list[str]

    recommendations: list[dict[str, Any]]
    comparisons: list[dict[str, Any]]
    citations: list[dict[str, Any]]

    shopping_knowledge_answer: str | None
    knowledge_used: bool

    answer: str
    tool_calls: list[dict[str, Any]]
    metadata: dict[str, Any]

    error_code: str | None
    error_message: str | None

    runtime: dict[str, Any]

