# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/26 22:31
IDE       :PyCharm
作者      :董宏升

模型调用日志模型。
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
import uuid
from decimal import Decimal

from sqlalchemy import ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import LogBaseMixin


class ModelCallLog(LogBaseMixin, Base):
    """
    模型调用日志表。

    表名：model_call_log

    用途：
    - 记录 LLM / Embedding / Rerank 调用摘要
    - 后续模型网关必须写入该表
    """

    __tablename__ = "model_call_log"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="调用用户 ID，可为空",
    )

    provider: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        comment="模型 Provider",
    )

    model_name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
        comment="模型名称",
    )

    model_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
        comment="模型类型：llm/embedding/rerank",
    )

    call_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="chat",
        index=True,
        comment="调用类型：chat/completion/embedding/rerank",
    )

    prompt_template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("prompt_template.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Prompt 模板 ID",
    )

    prompt_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("prompt_version.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Prompt 版本 ID",
    )

    input_tokens: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="输入 token 数",
    )

    output_tokens: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="输出 token 数",
    )

    total_tokens: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="总 token 数",
    )

    cost_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 6),
        nullable=True,
        comment="调用成本金额预留",
    )

    currency: Mapped[str | None] = mapped_column(
        String(16),
        nullable=True,
        comment="成本币种",
    )

    latency_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="调用耗时毫秒",
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="success",
        index=True,
        comment="调用状态：success/failed/timeout/canceled",
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

    input_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="输入摘要，禁止保存敏感全文",
    )

    output_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="输出摘要，禁止保存大段全文",
    )

    metadata_json: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="扩展元数据 JSON",
    )

    prompt_version = relationship(
        "PromptVersion",
        back_populates="model_call_logs",
        lazy="selectin",
    )

    __table_args__ = (
        Index(
            "ix_model_call_log_tenant_created_at",
            "tenant_id",
            "created_at",
        ),
        Index(
            "ix_model_call_log_tenant_provider_model",
            "tenant_id",
            "provider",
            "model_name",
        ),
        Index(
            "ix_model_call_log_tenant_status",
            "tenant_id",
            "status",
        ),
    )
