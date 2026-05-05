# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/05/05 08:30
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
"""
认证账号模型。

auth_account 是窗口 13 新增的轻量登录账号表。
它不替代 user_profile，而是通过 user_id 关联业务用户画像。
"""

from datetime import datetime
import uuid

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import BusinessBaseMixin


class AuthAccount(BusinessBaseMixin, Base):
    """
    登录账号表。

    角色：
    - admin
    - operator
    - viewer

    状态：
    - active
    - disabled
    """

    __tablename__ = "auth_account"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user_profile.id", ondelete="CASCADE"),
        nullable=False,
        comment="关联 user_profile.id",
    )

    username: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="登录用户名",
    )

    password_hash: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        comment="密码 hash，不存储明文密码",
    )

    role: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="角色：admin/operator/viewer",
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="active",
        comment="账号状态：active/disabled",
    )

    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="最后登录时间",
    )

    user = relationship(
        "UserProfile",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "username",
            name="uq_auth_account_tenant_username",
        ),
        CheckConstraint(
            "role in ('admin', 'operator', 'viewer')",
            name="ck_auth_account_role",
        ),
        CheckConstraint(
            "status in ('active', 'disabled')",
            name="ck_auth_account_status",
        ),
        Index(
            "ix_auth_account_tenant_user",
            "tenant_id",
            "user_id",
        ),
        Index(
            "ix_auth_account_tenant_role",
            "tenant_id",
            "role",
        ),
        Index(
            "ix_auth_account_tenant_status",
            "tenant_id",
            "status",
        ),
    )
