# -*- coding: utf-8 -*-
"""
创建时间    :2026/04/26 16:25
IDE       :PyCharm
作者      :董宏升
"""

# 每次解决问题，我都在成长，不要着急，不要气馁！
from typing import Any, Optional

from pydantic import BaseModel, Field


class ApiResponse(BaseModel):
    """
    统一 API 响应结构。

    所有接口必须返回该结构，不允许直接返回裸数组、裸字符串或模块自定义格式。
    """

    success: bool = Field(..., description="请求是否成功")
    code: str = Field(..., description="业务状态码")
    message: str = Field(..., description="响应消息")
    data: Optional[Any] = Field(default=None, description="响应数据")
    request_id: Optional[str] = Field(default=None, description="请求追踪 ID")


def success_response(
        data: Optional[Any] = None,
        message: str = "success",
        code: str = "OK",
        request_id: Optional[str] = None,
) -> ApiResponse:
    """
    构造成功响应。
    """
    return ApiResponse(
        success=True,
        code=code,
        message=message,
        data=data if data is not None else {},
        request_id=request_id,
    )


def error_response(
        code: str,
        message: str,
        request_id: Optional[str] = None,
        data: Optional[Any] = None,
) -> ApiResponse:
    """
    构造失败响应。
    """
    return ApiResponse(
        success=False,
        code=code,
        message=message,
        data=data,
        request_id=request_id,
    )
