from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import BusinessBaseMixin


class ContentAsset(BusinessBaseMixin, Base):
    """内容资产表。

    一条记录代表一个内容版本。
    通过 asset_group_id + version 管理同一份内容的多版本。
    """

    __tablename__ = "content_asset"

    asset_group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        default=uuid.uuid4,
        comment="内容版本组 ID，同一组内容的多个版本共享该 ID",
    )
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        comment="内容版本号，从 1 开始递增",
    )

    content_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="内容类型：product_title/product_selling_points/product_detail/campaign_copy",
    )
    biz_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="业务类型：product/campaign",
    )
    biz_id: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        comment="业务对象标识。商品内容可存 product_no，活动内容可存活动上下文标识",
    )

    title: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="内容标题或摘要",
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="生成后的内容正文",
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="draft",
        comment="内容状态：draft/reviewing/approved/rejected/archived",
    )
    review_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="pending",
        comment="审核状态：pending/passed/failed/manual_required",
    )
    source: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="llm_generated",
        comment="内容来源：llm_generated/manual_created/regenerated",
    )

    prompt_template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("prompt_template.id", ondelete="SET NULL"),
        nullable=True,
        comment="生成内容使用的 Prompt 模板 ID",
    )
    prompt_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("prompt_version.id", ondelete="SET NULL"),
        nullable=True,
        comment="生成内容使用的 Prompt 版本 ID",
    )
    model_call_log_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("model_call_log.id", ondelete="SET NULL"),
        nullable=True,
        comment="生成内容对应的模型调用日志 ID",
    )

    generation_input_json: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="生成输入快照",
    )
    generation_output_json: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="生成输出快照",
    )
    rule_check_result_json: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="敏感词和品牌规则检查结果",
    )
    metadata_json: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="扩展元数据",
    )

    created_by: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        comment="创建人标识，当前认证未完成时可为空或传 user_no",
    )
    approved_by: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        comment="审批人标识",
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="审批通过时间",
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "asset_group_id",
            "version",
            name="uq_content_asset_tenant_group_version",
        ),
        Index("ix_content_asset_tenant_content_type", "tenant_id", "content_type"),
        Index("ix_content_asset_tenant_biz", "tenant_id", "biz_type", "biz_id"),
        Index("ix_content_asset_tenant_status", "tenant_id", "status"),
    )
