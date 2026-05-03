# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/05/02 20:23
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from typing import Any, TypedDict
from uuid import UUID


class CustomerServiceAgentState(TypedDict, total=False):
    """智能客服 Agent 状态。

    这是 LangGraph 工作流内部流转的状态，不等于 API 响应结构。
    不要把完整 Prompt、大段模型输出、敏感隐私原文长期塞在这里。
    """

    tenant_id: UUID
    user_id: UUID | None
    user_no: str | None
    session_id: str
    request_id: str | None

    message: str
    conversation_summary: str | None
    context: dict[str, Any]

    agent_task_id: UUID | None
    intent: str | None
    confidence: float | None
    entities: dict[str, Any]

    selected_tools: list[str]
    tool_results: list[dict[str, Any]]

    rag_answer: str | None
    citations: list[dict[str, Any]]

    answer: str | None

    handoff_required: bool
    handoff_reason: str | None

    error_code: str | None
    error_message: str | None

    metadata: dict[str, Any]
