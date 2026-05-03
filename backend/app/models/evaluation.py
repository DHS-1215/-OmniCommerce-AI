# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/26 22:36
IDE       :PyCharm
作者      :董宏升

评测用例与评测结果模型。
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
import uuid
from decimal import Decimal

from sqlalchemy import ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import BusinessBaseMixin, LogBaseMixin


class EvaluationCase(BusinessBaseMixin, Base):
    """
    评测用例表。

    表名：evaluation_case
    """

    __tablename__ = "evaluation_case"

    case_no: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="评测用例业务编号",
    )

    case_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        comment="用例类型：rag/agent/prompt/tool",
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="用例名称",
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="用例说明",
    )

    input_json: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        comment="输入 JSON",
    )

    expected_output_json: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="期望输出 JSON",
    )

    reference_context_json: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="参考上下文 JSON",
    )

    tags_json: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="标签 JSON",
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="active",
        index=True,
        comment="用例状态：active/inactive/archived",
    )

    metadata_json: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="扩展元数据 JSON",
    )

    results = relationship(
        "EvaluationResult",
        back_populates="case",
        lazy="selectin",
    )

    __table_args__ = (
        Index(
            "ix_evaluation_case_tenant_type_status",
            "tenant_id",
            "case_type",
            "status",
        ),
        Index(
            "ix_evaluation_case_tenant_case_no",
            "tenant_id",
            "case_no",
        ),
    )


class EvaluationResult(LogBaseMixin, Base):
    """
    评测结果表。

    表名：evaluation_result
    """

    __tablename__ = "evaluation_result"

    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evaluation_case.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="评测用例 ID",
    )

    run_no: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        index=True,
        comment="评测运行批次编号",
    )

    target_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        comment="评测目标类型：rag/agent/prompt/tool",
    )

    target_id: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        index=True,
        comment="评测目标 ID，例如 prompt_version_id 或检索策略 ID",
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="success",
        index=True,
        comment="评测状态：success/failed/skipped",
    )

    score: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4),
        nullable=True,
        comment="综合得分",
    )

    answer_relevance: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4),
        nullable=True,
        comment="答案相关性",
    )

    faithfulness: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4),
        nullable=True,
        comment="忠实度",
    )

    context_recall: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4),
        nullable=True,
        comment="上下文召回",
    )

    context_precision: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4),
        nullable=True,
        comment="上下文精确率",
    )

    tool_call_success_rate: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4),
        nullable=True,
        comment="工具调用成功率",
    )

    agent_task_success_rate: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4),
        nullable=True,
        comment="Agent 任务成功率",
    )

    latency_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="耗时毫秒",
    )

    token_cost: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 6),
        nullable=True,
        comment="Token 成本",
    )

    input_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="评测输入摘要",
    )

    output_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="评测输出摘要",
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="错误信息摘要",
    )

    metrics_json: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="完整指标 JSON",
    )

    metadata_json: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="扩展元数据 JSON",
    )

    case = relationship(
        "EvaluationCase",
        back_populates="results",
        lazy="selectin",
    )

    __table_args__ = (
        Index(
            "ix_evaluation_result_tenant_run",
            "tenant_id",
            "run_no",
        ),
        Index(
            "ix_evaluation_result_tenant_target",
            "tenant_id",
            "target_type",
            "target_id",
        ),
        Index(
            "ix_evaluation_result_tenant_case_created",
            "tenant_id",
            "case_id",
            "created_at",
        ),
    )
