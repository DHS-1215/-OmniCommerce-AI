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

from app.models.agent import AgentStepLog


def _truncate(value: str | None, max_length: int = 500) -> str | None:
    if value is None:
        return None
    if len(value) <= max_length:
        return value
    return value[:max_length] + "...[truncated]"


class AgentStepLogService:
    """Agent 步骤日志服务。

    每个 LangGraph 关键节点都应该记录一条 agent_step_log。
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_step(
            self,
            *,
            tenant_id: UUID,
            agent_task_id: UUID,
            step_name: str,
            step_order: int,
            input_summary: str | None = None,
            request_id: str | None = None,
            status: str = "running",
    ) -> AgentStepLog:
        step = AgentStepLog(
            tenant_id=tenant_id,
            request_id=request_id,
            agent_task_id=agent_task_id,
            step_name=step_name,
            step_order=step_order,
            input_summary=_truncate(input_summary),
            status=status,
        )

        self.db.add(step)
        await self.db.commit()
        await self.db.refresh(step)
        return step

    async def mark_success(
            self,
            *,
            step: AgentStepLog,
            output_summary: str | None = None,
            latency_ms: int | None = None,
    ) -> AgentStepLog:
        step.status = "success"
        step.output_summary = _truncate(output_summary)
        step.latency_ms = latency_ms

        await self.db.commit()
        await self.db.refresh(step)
        return step

    async def mark_failed(
            self,
            *,
            step: AgentStepLog,
            error_message: str | None = None,
            latency_ms: int | None = None,
    ) -> AgentStepLog:
        step.status = "failed"
        step.output_summary = _truncate(error_message)
        step.latency_ms = latency_ms

        if hasattr(step, "error_message"):
            step.error_message = _truncate(error_message)

        await self.db.commit()
        await self.db.refresh(step)
        return step
