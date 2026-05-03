# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/27 14:26
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from app.schemas.common import JsonDict, ORMBaseModel, TenantRequest

TicketSource = Literal["manual", "agent", "api"]
TicketCategory = Literal["product", "order", "aftersale", "complaint", "other"]
TicketPriority = Literal["low", "normal", "high", "urgent"]


class CustomerServiceTicketCreateRequest(TenantRequest):
    """
    客服工单创建请求。

    窗口 3 只支持基础创建，不做 Agent 转人工。
    后续窗口 7 可通过 service 层使用 source=agent。
    """

    user_no: str | None = Field(default=None, max_length=64, description="用户业务编号")
    order_no: str | None = Field(default=None, max_length=64, description="订单业务编号")

    source: TicketSource = Field(default="api", description="工单来源")
    channel: str | None = Field(default=None, max_length=32, description="渠道")
    category: TicketCategory = Field(..., description="工单分类")
    priority: TicketPriority = Field(default="normal", description="优先级")

    title: str = Field(..., min_length=1, max_length=255, description="工单标题")
    content: str | None = Field(default=None, description="工单内容")

    assigned_operator_id: str | None = Field(
        default=None,
        max_length=128,
        description="分配客服人员 ID",
    )
    metadata_json: JsonDict | None = Field(default=None, description="扩展元数据 JSON")


class CustomerServiceTicketListItemResponse(ORMBaseModel):
    """
    客服工单列表项响应。
    """

    id: UUID = Field(..., description="客服工单主键 ID")
    tenant_id: UUID = Field(..., description="租户 ID")

    ticket_no: str = Field(..., description="客服工单业务编号")
    user_id: UUID | None = Field(default=None, description="用户 ID")
    order_id: UUID | None = Field(default=None, description="订单 ID")

    source: str = Field(..., description="工单来源")
    channel: str | None = Field(default=None, description="渠道")
    category: str = Field(..., description="工单分类")
    priority: str = Field(..., description="优先级")
    status: str = Field(..., description="工单状态")

    title: str = Field(..., description="工单标题")
    assigned_operator_id: str | None = Field(default=None, description="分配客服人员 ID")

    opened_at: datetime | None = Field(default=None, description="打开时间")
    resolved_at: datetime | None = Field(default=None, description="解决时间")
    closed_at: datetime | None = Field(default=None, description="关闭时间")

    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


class CustomerServiceTicketDetailResponse(CustomerServiceTicketListItemResponse):
    """
    客服工单详情响应。
    """

    content: str | None = Field(default=None, description="工单内容")
    resolution: str | None = Field(default=None, description="处理结果")
    related_agent_task_id: UUID | None = Field(default=None, description="关联 Agent 任务 ID")
    metadata_json: JsonDict | None = Field(default=None, description="扩展元数据 JSON")
