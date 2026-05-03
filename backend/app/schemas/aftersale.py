# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/27 14:26
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import Field

from app.schemas.common import JsonDict, JsonList, ORMBaseModel, TenantRequest

AfterSaleType = Literal["refund", "return", "exchange", "repair"]


class AfterSaleCreateRequest(TenantRequest):
    """
    售后单创建请求。

    使用 user_no / order_no 作为外部业务入参，
    service 层负责解析成 user_id / order_id。
    """

    user_no: str = Field(..., min_length=1, max_length=64, description="用户业务编号")
    order_no: str = Field(..., min_length=1, max_length=64, description="订单业务编号")
    order_item_id: UUID | None = Field(default=None, description="订单明细 ID，可选")

    after_sale_type: AfterSaleType = Field(..., description="售后类型")
    reason: str = Field(..., min_length=1, max_length=255, description="售后原因")
    description: str | None = Field(default=None, description="售后描述")

    refund_amount: Decimal | None = Field(default=None, ge=0, description="退款金额")
    currency: str = Field(default="CNY", max_length=16, description="币种")

    evidence_json: JsonList | None = Field(default=None, description="凭证 JSON")
    metadata_json: JsonDict | None = Field(default=None, description="扩展元数据 JSON")


class AfterSaleListItemResponse(ORMBaseModel):
    """
    售后单列表项响应。
    """

    id: UUID = Field(..., description="售后单主键 ID")
    tenant_id: UUID = Field(..., description="租户 ID")

    ticket_no: str = Field(..., description="售后单业务编号")
    user_id: UUID = Field(..., description="用户 ID")
    order_id: UUID = Field(..., description="订单 ID")
    order_item_id: UUID | None = Field(default=None, description="订单明细 ID")

    after_sale_type: str = Field(..., description="售后类型")
    reason: str = Field(..., description="售后原因")
    status: str = Field(..., description="售后状态")
    refund_amount: Decimal | None = Field(default=None, description="退款金额")
    currency: str = Field(..., description="币种")

    submitted_at: datetime | None = Field(default=None, description="提交时间")
    resolved_at: datetime | None = Field(default=None, description="处理完成时间")

    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


class AfterSaleDetailResponse(AfterSaleListItemResponse):
    """
    售后单详情响应。
    """

    description: str | None = Field(default=None, description="售后描述")
    evidence_json: JsonList | None = Field(default=None, description="凭证 JSON")
    audit_snapshot_json: JsonDict | None = Field(default=None, description="审核快照 JSON")
    metadata_json: JsonDict | None = Field(default=None, description="扩展元数据 JSON")
