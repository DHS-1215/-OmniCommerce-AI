from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import LogBaseMixin


class ContentReview(LogBaseMixin, Base):
    """内容审核记录表。

    用于记录规则审核、模型辅助审核和人工审批动作。
    """

    __tablename__ = "content_review"

    content_asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("content_asset.id", ondelete="CASCADE"),
        nullable=False,
        comment="关联内容资产 ID",
    )

    review_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="审核类型：rule_check/model_review/manual_review",
    )
    review_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="审核结果：passed/failed/manual_required",
    )
    reviewer_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="system",
        comment="审核方类型：system/model/human",
    )
    reviewer_id: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        comment="审核人标识，系统或模型审核可为空",
    )

    sensitive_check_result_json: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="敏感词检查结果",
    )
    brand_check_result_json: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="品牌规则检查结果",
    )
    model_review_result_json: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="模型辅助审核结果",
    )
    comments: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="审核意见",
    )

    __table_args__ = (
        Index("ix_content_review_tenant_asset", "tenant_id", "content_asset_id"),
        Index("ix_content_review_tenant_type", "tenant_id", "review_type"),
        Index("ix_content_review_tenant_status", "tenant_id", "review_status"),
    )
