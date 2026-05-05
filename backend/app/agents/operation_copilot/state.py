# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/05/04 08:56
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from typing import Any, TypedDict
from uuid import UUID


class OperationCopilotState(TypedDict, total=False):
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
    metric_keys: list[str]
    metric_plans: list[dict[str, Any]]
    sql: str | None
    sql_guard: dict[str, Any] | None
    query_result: dict[str, Any] | None

    answer: str
    report: str | None
    tool_calls: list[dict[str, Any]]
    metrics: list[dict[str, Any]]
    metadata: dict[str, Any]

    handoff_required: bool
    error_code: str | None
    error_message: str | None

    runtime: dict[str, Any]
