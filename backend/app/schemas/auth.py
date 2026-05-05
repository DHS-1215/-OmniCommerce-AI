# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/05/05 08:37
IDE       :PyCharm
作者      :董宏升

认证模块 Schema。
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    """
    登录请求。

    tenant_id 设计为可选：
    - demo 默认账号用户名保持全局唯一时，可以只传 username + password；
    - 如果后续多个租户存在同名 username，可传 tenant_id 消除歧义。
    """

    username: str = Field(..., min_length=1, max_length=128)
    password: str = Field(..., min_length=1, max_length=256)
    tenant_id: UUID | None = None


class AuthUserInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    account_id: UUID
    user_id: UUID
    user_no: str
    username: str
    tenant_id: UUID
    role: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: AuthUserInfo


class MeResponse(BaseModel):
    user: AuthUserInfo
