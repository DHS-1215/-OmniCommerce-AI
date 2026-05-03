# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/27 21:10
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from typing import Any

from fastapi import Request
from pydantic import BaseModel


def get_request_id(request: Request) -> str | None:
    """
    从 request.state 获取 request_id。
    """

    return getattr(request.state, "request_id", None)


def to_response_data(data: Any) -> Any:
    """
    将 Pydantic 模型转换成 JSON 友好的结构。

    原因：
    - schema 中包含 UUID / Decimal / datetime
    - ApiResponse.data 是 Any
    - 显式 model_dump(mode="json") 更稳
    """

    if isinstance(data, BaseModel):
        return data.model_dump(mode="json")

    if isinstance(data, list):
        return [to_response_data(item) for item in data]

    if isinstance(data, dict):
        return {key: to_response_data(value) for key, value in data.items()}

    return data