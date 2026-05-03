# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/05/02 20:14
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import AgentTask


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _new_task_no() -> str:
    return f"AGT{_utc_now().strftime('%Y%m%d%H%M%S')}{uuid4().hex[:8].upper()}"


def _truncate(value: str | None, max_length: int = 500) -> str | None:
    if value is None:
        return None
    if len(value) <= max_length:
        return value
    return value[:max_length] + "...[truncated]"


class AgentTaskService:
    """Agent 任务日志服务。

    负责 agent_task 的创建和状态更新。
    不负责编排 LangGraph，也不负责调用工具。
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_task(
            self,
            *,
            tenant_id: UUID,
            agent_type: str,
            session_id: str,
            input_summary: str,
            request_id: str | None = None,
            user_id: UUID | None = None,
            intent: str | None = None,
    ) -> AgentTask:
        task = AgentTask(
            tenant_id=tenant_id,
            request_id=request_id,
            agent_type=agent_type,
            session_id=session_id,
            task_no=_new_task_no(),
            input_summary=_truncate(input_summary),
            status="running",
            intent=intent,
            handoff_required=False,
        )

        # 兼容模型里存在 user_id 字段的情况；没有就不强塞，避免炸。
        if hasattr(task, "user_id"):
            task.user_id = user_id

        self.db.add(task)
        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def mark_success(
            self,
            *,
            task: AgentTask,
            output_summary: str | None = None,
            intent: str | None = None,
            handoff_required: bool | None = None,
            handoff_reason: str | None = None,
    ) -> AgentTask:
        task.status = "success"
        task.output_summary = _truncate(output_summary)
        if intent is not None:
            task.intent = intent
        if handoff_required is not None:
            task.handoff_required = handoff_required
        if hasattr(task, "handoff_reason"):
            task.handoff_reason = _truncate(handoff_reason)

        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def mark_failed(
            self,
            *,
            task: AgentTask,
            error_message: str | None = None,
            intent: str | None = None,
    ) -> AgentTask:
        task.status = "failed"
        task.output_summary = _truncate(error_message)
        if intent is not None:
            task.intent = intent
        if hasattr(task, "error_message"):
            task.error_message = _truncate(error_message)

        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def mark_handoff_required(
            self,
            *,
            task: AgentTask,
            reason: str,
            intent: str | None = None,
            output_summary: str | None = None,
    ) -> AgentTask:
        task.status = "handoff"
        task.handoff_required = True
        task.output_summary = _truncate(output_summary or reason)
        if intent is not None:
            task.intent = intent
        if hasattr(task, "handoff_reason"):
            task.handoff_reason = _truncate(reason)

        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def get_by_id(
            self,
            *,
            tenant_id: UUID,
            task_id: UUID,
    ) -> AgentTask | None:
        task = await self.db.get(AgentTask, task_id)
        if task is None:
            return None
        if task.tenant_id != tenant_id:
            return None
        return task
