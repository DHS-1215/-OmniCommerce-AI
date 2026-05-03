# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/26 20:56
IDE       :PyCharm
作者      :董宏升

Prompt 模板与版本模型。
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
import uuid

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import BusinessBaseMixin


class PromptTemplate(BusinessBaseMixin, Base):
    """
    Prompt 模板表。

    表名：prompt_template
    """

    __tablename__ = "prompt_template"

    template_key: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="模板唯一业务 Key",
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="模板名称",
    )

    scene: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
        comment="Prompt 场景，例如 customer_service_intent/rag_answer_generation",
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="模板说明",
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="active",
        index=True,
        comment="模板状态：active/inactive/archived",
    )

    metadata_json: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="扩展元数据 JSON",
    )

    versions = relationship(
        "PromptVersion",
        back_populates="template",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "template_key",
            name="uq_prompt_template_tenant_template_key",
        ),
        Index(
            "ix_prompt_template_tenant_scene_status",
            "tenant_id",
            "scene",
            "status",
        ),
    )


class PromptVersion(BusinessBaseMixin, Base):
    """
    Prompt 版本表。

    表名：prompt_version
    """

    __tablename__ = "prompt_version"

    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("prompt_template.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Prompt 模板 ID",
    )

    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="版本号，从 1 开始递增",
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Prompt 模板内容",
    )

    variable_schema_json: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="变量 schema JSON",
    )

    model_config_json: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="推荐模型参数 JSON",
    )

    gray_config_json: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="灰度配置 JSON 预留",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        comment="是否当前启用版本",
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="draft",
        index=True,
        comment="版本状态：draft/active/inactive/archived",
    )

    change_log: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="版本变更说明",
    )

    template = relationship(
        "PromptTemplate",
        back_populates="versions",
        lazy="selectin",
    )

    model_call_logs = relationship(
        "ModelCallLog",
        back_populates="prompt_version",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "template_id",
            "version",
            name="uq_prompt_version_tenant_template_version",
        ),
        Index(
            "ix_prompt_version_tenant_template_active",
            "tenant_id",
            "template_id",
            "is_active",
        ),
    )
