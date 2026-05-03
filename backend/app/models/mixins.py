# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/26 20:37
IDE       :PyCharm
作者      :董宏升

SQLAlchemy 模型通用 Mixin。

执行窗口 2 使用：
- UUIDPrimaryKeyMixin：统一 UUID 主键
- TenantMixin：多租户字段
- TimestampMixin：创建 / 更新时间
- SoftDeleteMixin：软删除字段
- BusinessBaseMixin：核心业务表通用字段
- LogBaseMixin：日志类表通用字段
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！


import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class UUIDPrimaryKeyMixin:
    """统一 UUID 主键。"""

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
        comment="主键 ID",
    )


class TenantMixin:
    """多租户字段。"""

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="租户 ID",
    )


class TimestampMixin:
    """创建时间 / 更新时间。"""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="创建时间",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="更新时间",
    )


class SoftDeleteMixin:
    """软删除字段。"""

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="软删除时间",
    )


class RequestIdMixin:
    """请求追踪字段，日志类表必须包含。"""

    request_id: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        index=True,
        comment="请求追踪 ID",
    )


class BusinessBaseMixin(
    UUIDPrimaryKeyMixin,
    TenantMixin,
    TimestampMixin,
    SoftDeleteMixin,
):
    """
    核心业务表通用字段。

    包含：
    - id
    - tenant_id
    - created_at
    - updated_at
    - deleted_at
    """

    pass


class LogBaseMixin(
    UUIDPrimaryKeyMixin,
    TenantMixin,
    RequestIdMixin,
):
    """
    日志类表通用字段。

    注意：
    日志表按全局规范至少包含：
    - id
    - tenant_id
    - request_id
    - created_at

    日志表通常不做 updated_at / deleted_at，避免审计日志被业务化修改。
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
        comment="创建时间",
    )
