# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/26 20:39
IDE       :PyCharm
作者      :董宏升

用户画像模型。
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from datetime import date

from sqlalchemy import Date, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import BusinessBaseMixin


class UserProfile(BusinessBaseMixin, Base):
    """
    用户画像表。

    表名：user_profile

    用途：
    - 支撑基础用户画像查询
    - 支撑客服 Agent 查询用户背景
    - 支撑导购 Agent 做偏好推荐
    """

    __tablename__ = "user_profile"

    user_no: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="用户业务编号",
    )

    nickname: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        comment="用户昵称",
    )

    phone_masked: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="脱敏手机号",
    )

    email_masked: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        comment="脱敏邮箱",
    )

    gender: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
        comment="性别：male/female/unknown 等",
    )

    birthday: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        comment="生日",
    )

    member_level: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="会员等级",
    )

    city: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        comment="城市",
    )

    preference_json: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="用户偏好 JSON",
    )

    tag_json: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="用户标签 JSON",
    )

    remark: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="备注",
    )

    orders = relationship(
        "OrderInfo",
        back_populates="user",
        lazy="selectin",
    )

    reviews = relationship(
        "ProductReview",
        back_populates="user",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "user_no",
            name="uq_user_profile_tenant_user_no",
        ),
        Index(
            "ix_user_profile_tenant_member_level",
            "tenant_id",
            "member_level",
        ),
    )
