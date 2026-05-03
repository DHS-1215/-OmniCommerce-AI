# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/27 14:21
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from datetime import date, datetime
from uuid import UUID

from pydantic import Field

from app.schemas.common import JsonDict, JsonList, ORMBaseModel


class UserProfileResponse(ORMBaseModel):
    """
    用户画像响应。
    """

    id: UUID = Field(..., description="用户画像主键 ID")
    tenant_id: UUID = Field(..., description="租户 ID")

    user_no: str = Field(..., description="用户业务编号")
    nickname: str | None = Field(default=None, description="用户昵称")
    phone_masked: str | None = Field(default=None, description="脱敏手机号")
    email_masked: str | None = Field(default=None, description="脱敏邮箱")
    gender: str | None = Field(default=None, description="性别")
    birthday: date | None = Field(default=None, description="生日")
    member_level: str | None = Field(default=None, description="会员等级")
    city: str | None = Field(default=None, description="城市")

    preference_json: JsonDict | None = Field(default=None, description="用户偏好 JSON")
    tag_json: JsonList | None = Field(default=None, description="用户标签 JSON")
    remark: str | None = Field(default=None, description="备注")

    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")