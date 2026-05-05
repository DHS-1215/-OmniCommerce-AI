# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/05/04 08:57
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from typing import Any

from app.agents.operation_copilot.workflow import build_operation_copilot_workflow
from app.llm.gateway import build_model_gateway
from app.schemas.operation_copilot import OperationCopilotChatRequest, OperationCopilotChatResponse
from app.services.agent_step_log_service import AgentStepLogService
from app.services.agent_task_service import AgentTaskService
from app.services.metric_service import MetricService
from app.services.model_call_log_service import ModelCallLogService
from app.services.prompt_service import PromptService
from app.services.sql_guard_service import SqlGuardService
from app.services.tool_call_log_service import ToolCallLogService
from app.tools.bi_tools import BITools


class OperationCopilotAgentService:
    def __init__(self, db: Any) -> None:
        self.db = db

        self.metric_service = MetricService()
        self.sql_guard_service = SqlGuardService()
        self.bi_tools = BITools(
            db=db,
            metric_service=self.metric_service,
            sql_guard_service=self.sql_guard_service,
            max_rows=100,
        )

        self.prompt_service = PromptService()

        self.model_call_log_service = ModelCallLogService(db)
        self.model_gateway = build_model_gateway(self.model_call_log_service)

        self.agent_task_service = AgentTaskService(db)
        self.step_log_service = AgentStepLogService(db)
        self.tool_call_log_service = ToolCallLogService(db)

        self.workflow = build_operation_copilot_workflow()

    async def chat(
            self,
            *,
            request: OperationCopilotChatRequest,
            request_id: str | None = None,
    ) -> OperationCopilotChatResponse:
        initial_state = {
            "tenant_id": request.tenant_id,
            "user_no": request.user_no,
            "session_id": request.session_id,
            "request_id": request_id,
            "message": request.message,
            "conversation_summary": request.conversation_summary,
            "context": request.context or {},
            "intent": "metric_query",
            "metric_keys": [],
            "metric_plans": [],
            "tool_calls": [],
            "metrics": [],
            "metadata": {},
            "handoff_required": False,
            "runtime": {
                "db": self.db,
                "metric_service": self.metric_service,
                "sql_guard_service": self.sql_guard_service,
                "bi_tools": self.bi_tools,
                "prompt_service": self.prompt_service,
                "model_gateway": self.model_gateway,
                "agent_task_service": self.agent_task_service,
                "step_log_service": self.step_log_service,
                "tool_call_log_service": self.tool_call_log_service,
            },
        }

        final_state = await self.workflow.ainvoke(initial_state)

        return OperationCopilotChatResponse(
            session_id=request.session_id,
            agent_task_id=final_state.get("agent_task_id"),
            intent=final_state.get("intent") or "metric_query",
            answer=final_state.get("answer") or "暂时无法完成该运营分析，请补充指标、时间范围或业务上下文。",
            metrics=final_state.get("metrics") or [],
            sql_summary={
                "sql": (final_state.get("sql_guard") or {}).get("normalized_sql") or final_state.get("sql"),
                "guard": final_state.get("sql_guard"),
            },
            query_result=final_state.get("query_result"),
            report=final_state.get("report"),
            tool_calls=final_state.get("tool_calls") or [],
            metadata=final_state.get("metadata") or {},
            handoff_required=bool(final_state.get("handoff_required") or False),
        )
