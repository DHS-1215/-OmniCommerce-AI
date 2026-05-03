# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/26 20:48
IDE       :PyCharm
作者      :董宏升

订单模型。
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import BusinessBaseMixin


class OrderInfo(BusinessBaseMixin, Base):
    """
    订单主表。

    表名：order_info
    """

    __tablename__ = "order_info"

    order_no: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="订单业务编号",
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user_profile.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="用户 ID",
    )

    order_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="created",
        index=True,
        comment="订单状态：created/paid/shipped/completed/canceled/refunding/refunded",
    )

    payment_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="unpaid",
        index=True,
        comment="支付状态：unpaid/paid/refunded/partial_refunded",
    )

    fulfillment_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="unfulfilled",
        index=True,
        comment="履约状态：unfulfilled/shipped/delivered",
    )

    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="订单原始总金额",
    )

    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=0,
        comment="优惠金额",
    )

    paid_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=0,
        comment="实付金额",
    )

    currency: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="CNY",
        comment="币种",
    )

    receiver_snapshot_json: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="收货人快照 JSON，注意只保存必要脱敏信息",
    )

    payment_snapshot_json: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="支付信息快照 JSON",
    )

    logistics_snapshot_json: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="物流信息快照 JSON",
    )

    metadata_json: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="扩展元数据 JSON",
    )

    placed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="下单时间",
    )

    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="支付时间",
    )

    canceled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="取消时间",
    )

    user = relationship(
        "UserProfile",
        back_populates="orders",
        lazy="selectin",
    )

    items = relationship(
        "OrderItem",
        back_populates="order",
        lazy="selectin",
    )

    after_sale_tickets = relationship(
        "AfterSaleTicket",
        back_populates="order",
        lazy="selectin",
    )

    customer_service_tickets = relationship(
        "CustomerServiceTicket",
        back_populates="order",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "order_no",
            name="uq_order_info_tenant_order_no",
        ),
        CheckConstraint(
            "total_amount >= 0",
            name="ck_order_info_total_amount_non_negative",
        ),
        CheckConstraint(
            "discount_amount >= 0",
            name="ck_order_info_discount_amount_non_negative",
        ),
        CheckConstraint(
            "paid_amount >= 0",
            name="ck_order_info_paid_amount_non_negative",
        ),
        Index(
            "ix_order_info_tenant_user_status",
            "tenant_id",
            "user_id",
            "order_status",
        ),
        Index(
            "ix_order_info_tenant_placed_at",
            "tenant_id",
            "placed_at",
        ),
    )


class OrderItem(BusinessBaseMixin, Base):
    """
    订单明细表。

    表名：order_item
    """

    __tablename__ = "order_item"

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("order_info.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="订单 ID",
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="商品 ID",
    )

    sku_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_sku.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="SKU ID",
    )

    product_title_snapshot: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="下单时商品标题快照",
    )

    sku_name_snapshot: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="下单时 SKU 名称快照",
    )

    sku_spec_snapshot_json: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="下单时 SKU 规格快照 JSON",
    )

    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="购买数量",
    )

    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="成交单价",
    )

    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="明细总金额",
    )

    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=0,
        comment="明细优惠金额",
    )

    paid_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=0,
        comment="明细实付金额",
    )

    item_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="normal",
        index=True,
        comment="明细状态：normal/refunding/refunded/canceled",
    )

    metadata_json: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="扩展元数据 JSON",
    )

    order = relationship(
        "OrderInfo",
        back_populates="items",
        lazy="selectin",
    )

    product = relationship(
        "Product",
        lazy="selectin",
    )

    sku = relationship(
        "ProductSku",
        back_populates="order_items",
        lazy="selectin",
    )

    review = relationship(
        "ProductReview",
        back_populates="order_item",
        uselist=False,
        lazy="selectin",
    )

    after_sale_tickets = relationship(
        "AfterSaleTicket",
        back_populates="order_item",
        lazy="selectin",
    )

    __table_args__ = (
        CheckConstraint(
            "quantity > 0",
            name="ck_order_item_quantity_positive",
        ),
        CheckConstraint(
            "unit_price >= 0",
            name="ck_order_item_unit_price_non_negative",
        ),
        CheckConstraint(
            "total_amount >= 0",
            name="ck_order_item_total_amount_non_negative",
        ),
        CheckConstraint(
            "discount_amount >= 0",
            name="ck_order_item_discount_amount_non_negative",
        ),
        CheckConstraint(
            "paid_amount >= 0",
            name="ck_order_item_paid_amount_non_negative",
        ),
        Index(
            "ix_order_item_tenant_order",
            "tenant_id",
            "order_id",
        ),
        Index(
            "ix_order_item_tenant_product_sku",
            "tenant_id",
            "product_id",
            "sku_id",
        ),
    )
