# -*- coding: utf-8 -*-
"""
创建时间    :2026/04/26 22:34
IDE       :PyCharm
作者      :董宏升

Agent 任务、步骤日志、工具调用日志模型。
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import BusinessBaseMixin, LogBaseMixin, RequestIdMixin


class AgentTask(RequestIdMixin, BusinessBaseMixin, Base):
    """
    Agent 任务表。

    表名：agent_task

    用途：
    - 记录一次 Agent 会话 / 任务的主信息
    - 后续客服 Agent、导购 Agent、BI Agent 都可复用
    """

    __tablename__ = "agent_task"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="用户 ID，可为空",
    )

    agent_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        comment="Agent 类型：customer_service/shopping_guide/operation_copilot/content_generation",
    )

    session_id: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        index=True,
        comment="会话 ID",
    )

    task_no: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        index=True,
        comment="Agent 任务业务编号",
    )

    input_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="用户输入摘要",
    )

    output_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Agent 输出摘要",
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="running",
        index=True,
        comment="任务状态：running/success/failed/canceled/handoff",
    )

    intent: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        index=True,
        comment="识别出的意图",
    )

    handoff_required: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
        comment="是否需要转人工",
    )

    error_code: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        comment="错误码",
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="错误信息摘要",
    )

    latency_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="任务总耗时毫秒",
    )

    metadata_json: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="扩展元数据 JSON",
    )

    step_logs = relationship(
        "AgentStepLog",
        back_populates="agent_task",
        lazy="selectin",
    )

    tool_call_logs = relationship(
        "ToolCallLog",
        back_populates="agent_task",
        lazy="selectin",
    )

    __table_args__ = (
        Index(
            "ix_agent_task_tenant_agent_status",
            "tenant_id",
            "agent_type",
            "status",
        ),
        Index(
            "ix_agent_task_tenant_session",
            "tenant_id",
            "session_id",
        ),
    )


class AgentStepLog(LogBaseMixin, Base):
    """
    Agent 步骤日志表。

    表名：agent_step_log
    """

    __tablename__ = "agent_step_log"

    agent_task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_task.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Agent 任务 ID",
    )

    step_name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
        comment="步骤名称 / LangGraph 节点名称",
    )

    step_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="步骤顺序",
    )

    input_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="步骤输入摘要",
    )

    output_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="步骤输出摘要",
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="success",
        index=True,
        comment="步骤状态：success/failed/skipped",
    )

    error_code: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        comment="错误码",
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="错误信息摘要",
    )

    latency_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="步骤耗时毫秒",
    )

    metadata_json: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="扩展元数据 JSON",
    )

    agent_task = relationship(
        "AgentTask",
        back_populates="step_logs",
        lazy="selectin",
    )

    __table_args__ = (
        Index(
            "ix_agent_step_log_tenant_task_order",
            "tenant_id",
            "agent_task_id",
            "step_order",
        ),
        Index(
            "ix_agent_step_log_tenant_step_status",
            "tenant_id",
            "step_name",
            "status",
        ),
    )


class ToolCallLog(LogBaseMixin, Base):
    """
    工具调用日志表。

    表名：tool_call_log
    """

    __tablename__ = "tool_call_log"

    agent_task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_task.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Agent 任务 ID",
    )

    agent_step_log_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_step_log.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Agent 步骤日志 ID",
    )

    tool_name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
        comment="工具名称",
    )

    tool_type: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
        comment="工具类型：business/rag/model/utility",
    )

    input_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="工具入参摘要",
    )

    output_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="工具返回摘要",
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="success",
        index=True,
        comment="调用状态：success/failed/timeout",
    )

    error_code: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        comment="错误码",
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="错误信息摘要",
    )

    latency_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="工具调用耗时毫秒",
    )

    metadata_json: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="扩展元数据 JSON",
    )

    agent_task = relationship(
        "AgentTask",
        back_populates="tool_call_logs",
        lazy="selectin",
    )

    agent_step_log = relationship(
        "AgentStepLog",
        lazy="selectin",
    )

    __table_args__ = (
        Index(
            "ix_tool_call_log_tenant_task",
            "tenant_id",
            "agent_task_id",
        ),
        Index(
            "ix_tool_call_log_tenant_tool_status",
            "tenant_id",
            "tool_name",
            "status",
        ),
    )