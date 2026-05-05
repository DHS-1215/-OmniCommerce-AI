# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/05/04 15:29
IDE       :PyCharm
作者      :董宏升

执行窗口 11：评测中心 Schema。
本文件只定义请求 / 响应结构，不写数据库查询，不调用 RAG / Agent / 模型网关。
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import ORMBaseModel

EvaluationCaseType = Literal[
    "rag",
    "agent",
    "customer_service_agent",
    "shopping_guide_agent",
    "operation_copilot_agent",
    "prompt",
    "retrieval",
    "tool",
    "content",
]

EvaluationCaseStatus = Literal["active", "inactive", "archived"]
EvaluationResultStatus = Literal["success", "failed", "skipped"]

EvaluationTargetType = Literal[
    "rag",
    "agent",
    "customer_service_agent",
    "shopping_guide_agent",
    "operation_copilot_agent",
    "prompt",
    "retrieval",
    "tool",
    "content",
]


class EvaluationCaseCreate(BaseModel):
    """创建评测用例请求。"""

    tenant_id: UUID = Field(..., description="租户 ID")
    case_no: str = Field(..., min_length=2, max_length=128, description="评测用例编号")
    case_type: EvaluationCaseType = Field(..., description="评测用例类型")
    name: str = Field(..., min_length=2, max_length=255, description="用例名称")
    description: str | None = Field(default=None, max_length=2000, description="用例说明")
    input_json: dict[str, Any] = Field(default_factory=dict, description="评测输入 JSON")
    expected_output_json: dict[str, Any] | None = Field(
        default=None,
        description="期望输出 JSON",
    )
    reference_context_json: list[Any] | None = Field(
        default=None,
        description="参考上下文 JSON",
    )
    tags_json: list[Any] | None = Field(default=None, description="标签 JSON")
    metadata_json: dict[str, Any] | None = Field(default=None, description="扩展元数据 JSON")
    status: EvaluationCaseStatus = Field(default="active", description="用例状态")


class EvaluationCaseUpdate(BaseModel):
    """更新评测用例请求。"""

    tenant_id: UUID = Field(..., description="租户 ID")
    name: str | None = Field(default=None, min_length=2, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    input_json: dict[str, Any] | None = None
    expected_output_json: dict[str, Any] | None = None
    reference_context_json: list[Any] | None = None
    tags_json: list[Any] | None = None
    metadata_json: dict[str, Any] | None = None
    status: EvaluationCaseStatus | None = None


class EvaluationCaseResponse(ORMBaseModel):
    """评测用例响应。"""

    id: UUID
    tenant_id: UUID
    case_no: str
    case_type: str
    name: str
    description: str | None = None
    input_json: dict[str, Any]
    expected_output_json: dict[str, Any] | None = None
    reference_context_json: list[Any] | None = None
    tags_json: list[Any] | None = None
    status: str
    metadata_json: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime


class EvaluationResultResponse(ORMBaseModel):
    """评测结果响应。"""

    id: UUID
    tenant_id: UUID
    request_id: str | None = None
    case_id: UUID
    run_no: str | None = None
    target_type: str
    target_id: str | None = None
    status: str

    score: Decimal | None = None
    answer_relevance: Decimal | None = None
    faithfulness: Decimal | None = None
    context_recall: Decimal | None = None
    context_precision: Decimal | None = None
    tool_call_success_rate: Decimal | None = None
    agent_task_success_rate: Decimal | None = None

    latency_ms: int | None = None
    token_cost: Decimal | None = None
    input_summary: str | None = None
    output_summary: str | None = None
    error_message: str | None = None
    metrics_json: dict[str, Any] | None = None
    metadata_json: dict[str, Any] | None = None
    created_at: datetime


class RagEvaluationRunRequest(BaseModel):
    """执行 RAG 评测请求。"""

    tenant_id: UUID = Field(..., description="租户 ID")
    case_ids: list[UUID] | None = Field(
        default=None,
        description="指定用例 ID；不传则执行该租户下 active 的 rag 用例",
    )
    run_no: str | None = Field(default=None, max_length=128, description="运行批次编号")
    target_id: str | None = Field(default=None, max_length=128, description="目标 ID")
    top_k: int | None = Field(default=None, ge=1, le=20, description="RAG 检索 top_k")
    metadata_json: dict[str, Any] | None = Field(default=None, description="扩展元数据")


class AgentEvaluationRunRequest(BaseModel):
    """执行 Agent 评测请求。"""

    tenant_id: UUID = Field(..., description="租户 ID")
    agent_type: Literal[
        "customer_service",
        "shopping_guide",
        "operation_copilot",
    ] = Field(..., description="Agent 类型")
    case_ids: list[UUID] | None = Field(
        default=None,
        description="指定用例 ID；不传则根据 agent_type 查询 active 用例",
    )
    run_no: str | None = Field(default=None, max_length=128, description="运行批次编号")
    target_id: str | None = Field(default=None, max_length=128, description="目标 ID")
    metadata_json: dict[str, Any] | None = Field(default=None, description="扩展元数据")


class PromptCompareRequest(BaseModel):
    """Prompt 版本对比请求。"""

    tenant_id: UUID = Field(..., description="租户 ID")
    prompt_version_ids: list[UUID] = Field(
        ...,
        min_length=2,
        description="要比较的 Prompt 版本 ID",
    )
    case_ids: list[UUID] | None = Field(
        default=None,
        description="指定评测用例；不传则使用 prompt 类型 active 用例",
    )
    run_no: str | None = Field(default=None, max_length=128)
    metadata_json: dict[str, Any] | None = None


class RetrievalCompareRequest(BaseModel):
    """检索策略对比请求。"""

    tenant_id: UUID = Field(..., description="租户 ID")
    strategies: list[dict[str, Any]] = Field(
        ...,
        min_length=2,
        description="检索策略列表，例如 vector_weight/keyword_weight/top_k",
    )
    case_ids: list[UUID] | None = Field(
        default=None,
        description="指定评测用例；不传则使用 retrieval/rag 类型 active 用例",
    )
    run_no: str | None = Field(default=None, max_length=128)
    metadata_json: dict[str, Any] | None = None


class EvaluationRunResponse(BaseModel):
    """评测执行响应。"""

    run_no: str
    target_type: str
    total: int
    success_count: int
    failed_count: int
    results: list[EvaluationResultResponse] = Field(default_factory=list)


class EvaluationReportResponse(BaseModel):
    """评测报告响应。"""

    tenant_id: UUID
    run_no: str | None = None
    target_type: str | None = None
    total: int
    success_count: int
    failed_count: int
    avg_score: Decimal | None = None
    avg_answer_relevance: Decimal | None = None
    avg_faithfulness: Decimal | None = None
    avg_context_recall: Decimal | None = None
    avg_context_precision: Decimal | None = None
    avg_tool_call_success_rate: Decimal | None = None
    avg_agent_task_success_rate: Decimal | None = None
    items: list[EvaluationResultResponse] = Field(default_factory=list)
