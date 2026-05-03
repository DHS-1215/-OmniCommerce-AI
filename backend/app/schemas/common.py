# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/27 14:16
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from datetime import datetime
from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

JsonDict = dict[str, Any]
JsonList = list[Any]

T = TypeVar("T")


class ORMBaseModel(BaseModel):
    """
    Pydantic v2 ORM 响应基类。

    用于支持 SQLAlchemy ORM 对象直接 model_validate。
    """

    model_config = ConfigDict(from_attributes=True)


class TenantRequest(BaseModel):
    """
    临时多租户请求基类。

    当前认证 / RBAC 尚未实现，窗口 3 先显式传 tenant_id。
    后续认证完成后，可改为从登录上下文读取 tenant_id。
    """

    tenant_id: UUID = Field(..., description="租户 ID")


class PageQuery(BaseModel):
    """
    分页查询参数。
    """

    page: int = Field(default=1, ge=1, description="页码，从 1 开始")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量")


class PageResponse(BaseModel, Generic[T]):
    """
    统一分页 data 结构。

    最外层仍由 core.response.success_response 包装。
    """

    items: list[T] = Field(default_factory=list, description="当前页数据")
    total: int = Field(..., ge=0, description="总数量")
    page: int = Field(..., ge=1, description="当前页码")
    page_size: int = Field(..., ge=1, description="每页数量")


class TimestampResponse(ORMBaseModel):
    """
    业务表通用时间字段。
    """

    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


