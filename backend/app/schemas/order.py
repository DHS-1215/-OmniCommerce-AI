# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/27 14:25
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import Field

from app.schemas.common import JsonDict, ORMBaseModel


class OrderItemResponse(ORMBaseModel):
    """
    订单明细响应。
    """

    id: UUID = Field(..., description="订单明细主键 ID")
    tenant_id: UUID = Field(..., description="租户 ID")

    order_id: UUID = Field(..., description="订单 ID")
    product_id: UUID = Field(..., description="商品 ID")
    sku_id: UUID = Field(..., description="SKU ID")

    product_title_snapshot: str = Field(..., description="商品标题快照")
    sku_name_snapshot: str = Field(..., description="SKU 名称快照")
    sku_spec_snapshot_json: JsonDict | None = Field(default=None, description="SKU 规格快照")

    quantity: int = Field(..., description="购买数量")
    unit_price: Decimal = Field(..., description="单价")
    total_amount: Decimal = Field(..., description="原始总金额")
    discount_amount: Decimal = Field(..., description="优惠金额")
    paid_amount: Decimal = Field(..., description="实付金额")
    item_status: str = Field(..., description="订单明细状态")

    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


class OrderListItemResponse(ORMBaseModel):
    """
    订单列表项响应。
    """

    id: UUID = Field(..., description="订单主键 ID")
    tenant_id: UUID = Field(..., description="租户 ID")

    order_no: str = Field(..., description="订单业务编号")
    user_id: UUID = Field(..., description="用户 ID")

    order_status: str = Field(..., description="订单状态")
    payment_status: str = Field(..., description="支付状态")
    fulfillment_status: str = Field(..., description="履约状态")

    total_amount: Decimal = Field(..., description="订单原始总金额")
    discount_amount: Decimal = Field(..., description="优惠金额")
    paid_amount: Decimal = Field(..., description="实付金额")
    currency: str = Field(..., description="币种")

    placed_at: datetime | None = Field(default=None, description="下单时间")
    paid_at: datetime | None = Field(default=None, description="支付时间")
    canceled_at: datetime | None = Field(default=None, description="取消时间")

    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


class OrderDetailResponse(OrderListItemResponse):
    """
    订单详情响应。
    """

    receiver_snapshot_json: JsonDict | None = Field(default=None, description="收货信息快照")
    payment_snapshot_json: JsonDict | None = Field(default=None, description="支付信息快照")
    logistics_snapshot_json: JsonDict | None = Field(default=None, description="物流信息快照")
    metadata_json: JsonDict | None = Field(default=None, description="扩展元数据 JSON")

    items: list[OrderItemResponse] = Field(default_factory=list, description="订单明细")
