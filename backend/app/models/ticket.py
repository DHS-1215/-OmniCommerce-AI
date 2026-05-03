# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/26 20:55
IDE       :PyCharm
作者      :董宏升

售后单、客服工单模型。
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import BusinessBaseMixin


class AfterSaleTicket(BusinessBaseMixin, Base):
    """
    售后单表。

    表名：after_sale_ticket

    用途：
    - 支撑售后申请创建和查询
    - 后续客服 Agent 可通过 service 层创建售后单
    """

    __tablename__ = "after_sale_ticket"

    ticket_no: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="售后单业务编号",
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user_profile.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="用户 ID",
    )

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("order_info.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="订单 ID",
    )

    order_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("order_item.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="订单明细 ID",
    )

    after_sale_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
        comment="售后类型：refund/return/exchange/repair",
    )

    reason: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="售后原因",
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="售后描述",
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="pending",
        index=True,
        comment="售后状态：pending/approved/rejected/processing/completed/canceled",
    )

    refund_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        comment="退款金额",
    )

    currency: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="CNY",
        comment="币种",
    )

    evidence_json: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="凭证 JSON，例如图片、视频、物流单据",
    )

    audit_snapshot_json: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="审核快照 JSON",
    )

    metadata_json: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="扩展元数据 JSON",
    )

    submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="提交时间",
    )

    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="处理完成时间",
    )

    user = relationship(
        "UserProfile",
        lazy="selectin",
    )

    order = relationship(
        "OrderInfo",
        back_populates="after_sale_tickets",
        lazy="selectin",
    )

    order_item = relationship(
        "OrderItem",
        back_populates="after_sale_tickets",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "ticket_no",
            name="uq_after_sale_ticket_tenant_ticket_no",
        ),
        Index(
            "ix_after_sale_ticket_tenant_user_status",
            "tenant_id",
            "user_id",
            "status",
        ),
        Index(
            "ix_after_sale_ticket_tenant_order_status",
            "tenant_id",
            "order_id",
            "status",
        ),
    )


class CustomerServiceTicket(BusinessBaseMixin, Base):
    """
    客服工单表。

    表名：customer_service_ticket

    用途：
    - 支撑客服工单创建和查询
    - 后续客服 Agent 高风险场景转人工时创建工单
    """

    __tablename__ = "customer_service_ticket"

    ticket_no: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="客服工单业务编号",
    )

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user_profile.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="用户 ID",
    )

    order_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("order_info.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="关联订单 ID",
    )

    source: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="manual",
        index=True,
        comment="工单来源：manual/agent/api",
    )

    channel: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
        comment="渠道：web/app/wechat/phone/email 等",
    )

    category: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        comment="工单分类：product/order/aftersale/complaint/other",
    )

    priority: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="normal",
        index=True,
        comment="优先级：low/normal/high/urgent",
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="open",
        index=True,
        comment="工单状态：open/processing/resolved/closed/canceled",
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="工单标题",
    )

    content: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="工单内容",
    )

    assigned_operator_id: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        index=True,
        comment="分配客服人员 ID，认证模块完成前先用字符串预留",
    )

    resolution: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="处理结果",
    )

    related_agent_task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_task.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="关联 Agent 任务 ID",
    )

    metadata_json: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="扩展元数据 JSON",
    )

    opened_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="打开时间",
    )

    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="解决时间",
    )

    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="关闭时间",
    )

    user = relationship(
        "UserProfile",
        lazy="selectin",
    )

    order = relationship(
        "OrderInfo",
        back_populates="customer_service_tickets",
        lazy="selectin",
    )

    related_agent_task = relationship(
        "AgentTask",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "ticket_no",
            name="uq_customer_service_ticket_tenant_ticket_no",
        ),
        Index(
            "ix_customer_service_ticket_tenant_status_priority",
            "tenant_id",
            "status",
            "priority",
        ),
        Index(
            "ix_customer_service_ticket_tenant_category_status",
            "tenant_id",
            "category",
            "status",
        ),
    )
