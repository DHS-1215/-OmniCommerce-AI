# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/05/02 20:15
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import ToolCallLog


def _truncate(value: str | None, max_length: int = 500) -> str | None:
    if value is None:
        return None
    if len(value) <= max_length:
        return value
    return value[:max_length] + "...[truncated]"


class ToolCallLogService:
    """工具调用日志服务。

    每次 Agent 工具调用都必须记录 tool_call_log。
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_tool_call_log(
            self,
            *,
            tenant_id: UUID,
            agent_task_id: UUID,
            tool_name: str,
            tool_type: str,
            input_summary: str | None = None,
            output_summary: str | None = None,
            status: str = "success",
            latency_ms: int | None = None,
            request_id: str | None = None,
            agent_step_log_id: UUID | None = None,
            error_code: str | None = None,
            error_message: str | None = None,
    ) -> ToolCallLog:
        log = ToolCallLog(
            tenant_id=tenant_id,
            request_id=request_id,
            agent_task_id=agent_task_id,
            agent_step_log_id=agent_step_log_id,
            tool_name=tool_name,
            tool_type=tool_type,
            input_summary=_truncate(input_summary),
            output_summary=_truncate(output_summary),
            status=status,
            latency_ms=latency_ms,
        )

        # 兼容模型里存在 error_code / error_message 字段的情况。
        if hasattr(log, "error_code"):
            log.error_code = error_code
        if hasattr(log, "error_message"):
            log.error_message = _truncate(error_message)

        self.db.add(log)
        await self.db.commit()
        await self.db.refresh(log)
        return log
