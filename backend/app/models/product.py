# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/26 20:46
IDE       :PyCharm
作者      :董宏升

商品、SKU、评价模型。
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
import uuid
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import BusinessBaseMixin


class Product(BusinessBaseMixin, Base):
    """
    商品 SPU 表。

    表名：product
    """

    __tablename__ = "product"

    product_no: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="商品业务编号",
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="商品标题",
    )

    subtitle: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="商品副标题",
    )

    brand: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        index=True,
        comment="品牌",
    )

    category: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        index=True,
        comment="一级或主类目",
    )

    category_path: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
        comment="类目路径",
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="商品描述",
    )

    main_image_url: Mapped[str | None] = mapped_column(
        String(1024),
        nullable=True,
        comment="主图 URL",
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="active",
        index=True,
        comment="商品状态：active/inactive/draft",
    )

    tag_json: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="商品标签 JSON",
    )

    attribute_json: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="商品属性 JSON",
    )

    metadata_json: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="扩展元数据 JSON",
    )

    skus = relationship(
        "ProductSku",
        back_populates="product",
        lazy="selectin",
    )

    reviews = relationship(
        "ProductReview",
        back_populates="product",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "product_no",
            name="uq_product_tenant_product_no",
        ),
        Index(
            "ix_product_tenant_category_status",
            "tenant_id",
            "category",
            "status",
        ),
    )


class ProductSku(BusinessBaseMixin, Base):
    """
    商品 SKU 表。

    表名：product_sku
    """

    __tablename__ = "product_sku"

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="商品 ID",
    )

    sku_no: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="SKU 业务编号",
    )

    sku_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="SKU 名称",
    )

    sku_code: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        comment="SKU 编码",
    )

    sale_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="销售价",
    )

    market_price: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        comment="划线价 / 市场价",
    )

    cost_price: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        comment="成本价，仅运营内部使用",
    )

    currency: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="CNY",
        comment="币种",
    )

    stock_quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="库存数量",
    )

    image_url: Mapped[str | None] = mapped_column(
        String(1024),
        nullable=True,
        comment="SKU 图片 URL",
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="active",
        index=True,
        comment="SKU 状态：active/inactive/out_of_stock",
    )

    spec_json: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="规格 JSON，例如颜色、尺码",
    )

    metadata_json: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="扩展元数据 JSON",
    )

    product = relationship(
        "Product",
        back_populates="skus",
        lazy="selectin",
    )

    order_items = relationship(
        "OrderItem",
        back_populates="sku",
        lazy="selectin",
    )

    reviews = relationship(
        "ProductReview",
        back_populates="sku",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "sku_no",
            name="uq_product_sku_tenant_sku_no",
        ),
        CheckConstraint(
            "sale_price >= 0",
            name="ck_product_sku_sale_price_non_negative",
        ),
        CheckConstraint(
            "stock_quantity >= 0",
            name="ck_product_sku_stock_quantity_non_negative",
        ),
        Index(
            "ix_product_sku_tenant_product_status",
            "tenant_id",
            "product_id",
            "status",
        ),
    )


class ProductReview(BusinessBaseMixin, Base):
    """
    商品评价表。

    表名：product_review
    """

    __tablename__ = "product_review"

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="商品 ID",
    )

    sku_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_sku.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="SKU ID",
    )

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user_profile.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="用户 ID",
    )

    order_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("order_item.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="订单明细 ID",
    )

    rating: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="评分，1-5",
    )

    content: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="评价内容",
    )

    image_json: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="评价图片 JSON",
    )

    sentiment: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
        comment="情感倾向：positive/neutral/negative",
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="visible",
        index=True,
        comment="评价状态：visible/hidden/pending",
    )

    metadata_json: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="扩展元数据 JSON",
    )

    product = relationship(
        "Product",
        back_populates="reviews",
        lazy="selectin",
    )

    sku = relationship(
        "ProductSku",
        back_populates="reviews",
        lazy="selectin",
    )

    user = relationship(
        "UserProfile",
        back_populates="reviews",
        lazy="selectin",
    )

    order_item = relationship(
        "OrderItem",
        back_populates="review",
        lazy="selectin",
    )

    __table_args__ = (
        CheckConstraint(
            "rating >= 1 AND rating <= 5",
            name="ck_product_review_rating_range",
        ),
        Index(
            "ix_product_review_tenant_product_status",
            "tenant_id",
            "product_id",
            "status",
        ),
    )
