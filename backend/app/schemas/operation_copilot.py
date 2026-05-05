# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/05/03 22:32
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class MetricDefinitionResponse(BaseModel):
    metric_key: str
    name: str
    description: str
    category: str
    formula: str | None = None
    source_tables: list[str] = Field(default_factory=list)
    dimensions: list[str] = Field(default_factory=list)
    filters: list[str] = Field(default_factory=list)
    status: str = "available"
    unavailable_reason: str | None = None


class MetricQueryPlan(BaseModel):
    metric_key: str
    metric_name: str
    status: str = "available"
    sql: str | None = None
    params: dict[str, Any] = Field(default_factory=dict)
    source_tables: list[str] = Field(default_factory=list)
    unavailable_reason: str | None = None


class SqlGuardResult(BaseModel):
    passed: bool
    readonly: bool = False
    normalized_sql: str | None = None
    tables: list[str] = Field(default_factory=list)
    rejected_reason: str | None = None
    error_code: str | None = None


class BIQueryResult(BaseModel):
    columns: list[str] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)
    row_count: int = 0
    limited: bool = False
    max_rows: int


class OperationCopilotChatRequest(BaseModel):
    tenant_id: UUID
    session_id: str
    user_no: str | None = None
    message: str
    conversation_summary: str | None = ""
    context: dict[str, Any] = Field(default_factory=dict)


class OperationCopilotChatResponse(BaseModel):
    session_id: str
    agent_task_id: UUID | None = None
    intent: str
    answer: str
    metrics: list[dict[str, Any]] = Field(default_factory=list)
    sql_summary: dict[str, Any] | None = None
    query_result: BIQueryResult | None = None
    report: str | None = None
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    handoff_required: bool = False
