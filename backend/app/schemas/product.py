# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/27 14:24
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import Field

from app.schemas.common import JsonDict, JsonList, ORMBaseModel


class ProductSkuResponse(ORMBaseModel):
    """
    SKU 响应。

    注意：普通业务接口不暴露 cost_price。
    """

    id: UUID = Field(..., description="SKU 主键 ID")
    tenant_id: UUID = Field(..., description="租户 ID")
    product_id: UUID = Field(..., description="商品主键 ID")

    sku_no: str = Field(..., description="SKU 业务编号")
    sku_name: str = Field(..., description="SKU 名称")
    sku_code: str | None = Field(default=None, description="SKU 编码")

    sale_price: Decimal = Field(..., description="销售价")
    market_price: Decimal | None = Field(default=None, description="市场价 / 划线价")
    currency: str = Field(..., description="币种")
    stock_quantity: int = Field(..., description="库存数量")
    image_url: str | None = Field(default=None, description="SKU 图片 URL")
    status: str = Field(..., description="SKU 状态")
    spec_json: JsonDict | None = Field(default=None, description="规格 JSON")

    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


class ProductSkuAdminResponse(ProductSkuResponse):
    """
    后台 SKU 响应。

    后台管理接口可查看成本价。
    """

    cost_price: Decimal | None = Field(default=None, description="成本价")


class ProductReviewResponse(ORMBaseModel):
    """
    商品评价响应。
    """

    id: UUID = Field(..., description="评价主键 ID")
    tenant_id: UUID = Field(..., description="租户 ID")

    product_id: UUID = Field(..., description="商品 ID")
    sku_id: UUID | None = Field(default=None, description="SKU ID")
    user_id: UUID | None = Field(default=None, description="用户 ID")
    order_item_id: UUID | None = Field(default=None, description="订单明细 ID")

    rating: int = Field(..., ge=1, le=5, description="评分，1-5")
    content: str | None = Field(default=None, description="评价内容")
    image_json: JsonList | None = Field(default=None, description="评价图片 JSON")
    sentiment: str | None = Field(default=None, description="情感倾向")
    status: str = Field(..., description="评价状态")

    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


class ProductListItemResponse(ORMBaseModel):
    """
    商品列表项响应。
    """

    id: UUID = Field(..., description="商品主键 ID")
    tenant_id: UUID = Field(..., description="租户 ID")

    product_no: str = Field(..., description="商品业务编号")
    title: str = Field(..., description="商品标题")
    subtitle: str | None = Field(default=None, description="商品副标题")
    brand: str | None = Field(default=None, description="品牌")
    category: str | None = Field(default=None, description="类目")
    category_path: str | None = Field(default=None, description="类目路径")
    main_image_url: str | None = Field(default=None, description="主图 URL")
    status: str = Field(..., description="商品状态")
    tag_json: JsonList | None = Field(default=None, description="商品标签 JSON")

    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


class ProductDetailResponse(ProductListItemResponse):
    """
    商品详情响应。
    """

    description: str | None = Field(default=None, description="商品描述")
    attribute_json: JsonDict | None = Field(default=None, description="商品属性 JSON")
    metadata_json: JsonDict | None = Field(default=None, description="扩展元数据 JSON")
    skus: list[ProductSkuResponse] = Field(default_factory=list, description="SKU 列表")


class ProductAdminItemResponse(ProductDetailResponse):
    """
    后台商品响应。

    后台接口允许看到 inactive / draft 商品，也可看到更多运营字段。
    """

    skus: list[ProductSkuAdminResponse] = Field(
        default_factory=list,
        description="后台 SKU 列表",
    )
