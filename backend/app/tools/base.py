# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/05/02 19:34
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
import json
from typing import Any

from pydantic import BaseModel, Field
from app.core.exceptions import BaseAppException



class ToolResult(BaseModel):
    """Agent 工具统一返回结构。

    所有 Agent 工具都必须返回 ToolResult，避免每个工具自定义一套结果格式。
    """

    success: bool = Field(..., description="工具是否执行成功")
    tool_name: str = Field(..., description="工具名称")
    data: Any | None = Field(default=None, description="工具返回数据")
    error_code: str | None = Field(default=None, description="失败错误码")
    error_message: str | None = Field(default=None, description="失败错误信息")

    @classmethod
    def ok(cls, tool_name: str, data: Any | None = None) -> "ToolResult":
        return cls(
            success=True,
            tool_name=tool_name,
            data=data,
            error_code=None,
            error_message=None,
        )

    @classmethod
    def fail(
            cls,
            tool_name: str,
            error_code: str,
            error_message: str,
            data: Any | None = None,
    ) -> "ToolResult":
        return cls(
            success=False,
            tool_name=tool_name,
            data=data,
            error_code=error_code,
            error_message=error_message,
        )


def summarize_value(value: Any, max_length: int = 500) -> str:
    """将工具入参 / 出参压缩成可写入日志的短摘要。

    注意：
    - 不保存完整大对象；
    - 不保存完整模型输出；
    - 不保存完整 Prompt；
    - 不保存过长用户隐私内容。
    """

    if value is None:
        return ""

    try:
        if isinstance(value, BaseModel):
            raw = value.model_dump(mode="json")
        else:
            raw = value

        text = json.dumps(raw, ensure_ascii=False, default=str)
    except Exception:
        text = str(value)

    if len(text) <= max_length:
        return text

    return text[:max_length] + "...[truncated]"


def tool_result_to_log_summary(result: ToolResult, max_length: int = 500) -> str:
    """将 ToolResult 转为 tool_call_log.output_summary。"""

    payload = {
        "success": result.success,
        "tool_name": result.tool_name,
        "data": result.data,
        "error_code": result.error_code,
        "error_message": result.error_message,
    }
    return summarize_value(payload, max_length=max_length)


def to_plain_data(value: Any) -> Any:
    """将 service 返回值转换成适合放入 ToolResult 的普通数据结构。"""

    if value is None:
        return None

    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")

    if isinstance(value, list):
        return [to_plain_data(item) for item in value]

    if isinstance(value, tuple):
        return [to_plain_data(item) for item in value]

    if isinstance(value, dict):
        return {key: to_plain_data(item) for key, item in value.items()}

    return value


def business_error_result(tool_name: str, exc: BaseAppException) -> ToolResult:
    """将项目统一业务异常转换为工具失败结果。"""

    return ToolResult.fail(
        tool_name=tool_name,
        error_code=getattr(exc, "code", "BUSINESS_ERROR"),
        error_message=getattr(exc, "message", str(exc)),
    )


def unexpected_error_result(tool_name: str, exc: Exception) -> ToolResult:
    """将非预期异常转换为工具失败结果。"""

    return ToolResult.fail(
        tool_name=tool_name,
        error_code="AGENT_TOOL_CALL_FAILED",
        error_message=f"{tool_name} 执行失败：{exc.__class__.__name__}",
    )
