# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any

from app.agents.shopping_guide.workflow import build_shopping_guide_workflow
from app.schemas.shopping_guide import ShoppingGuideChatRequest, ShoppingGuideChatResponse
from app.services.agent_step_log_service import AgentStepLogService
from app.services.agent_task_service import AgentTaskService
from app.services.prompt_service import PromptService
from app.services.recommendation_service import RecommendationService
from app.services.tool_call_log_service import ToolCallLogService
from app.tools.recommendation_tools import RecommendationTools
from app.llm.gateway import build_model_gateway
from app.services.model_call_log_service import ModelCallLogService


class ShoppingGuideAgentService:
    def __init__(self, db: Any) -> None:
        self.db = db

        self.recommendation_service = RecommendationService()
        self.recommendation_tools = RecommendationTools(
            db=db,
            recommendation_service=self.recommendation_service,
        )

        self.prompt_service = PromptService()

        self.model_call_log_service = ModelCallLogService(db)
        self.model_gateway = build_model_gateway(self.model_call_log_service)

        self.agent_task_service = AgentTaskService(db)
        self.step_log_service = AgentStepLogService(db)
        self.tool_call_log_service = ToolCallLogService(db)

        self.workflow = build_shopping_guide_workflow()

    async def chat(
        self,
        *,
        request: ShoppingGuideChatRequest,
        request_id: str | None = None,
    ) -> ShoppingGuideChatResponse:
        initial_state = {
            "tenant_id": request.tenant_id,
            "user_no": request.user_no,
            "session_id": request.session_id,
            "request_id": request_id,
            "message": request.message,
            "conversation_summary": request.conversation_summary,
            "context": request.context or {},
            "intent": "shopping_guide",
            "tool_calls": [],
            "recommendations": [],
            "comparisons": [],
            "citations": [],
            "metadata": {},
            "runtime": {
                "db": self.db,
                "recommendation_service": self.recommendation_service,
                "recommendation_tools": self.recommendation_tools,
                "prompt_service": self.prompt_service,
                "model_gateway": self.model_gateway,
                "agent_task_service": self.agent_task_service,
                "step_log_service": self.step_log_service,
                "tool_call_log_service": self.tool_call_log_service,
            },
        }

        final_state = await self.workflow.ainvoke(initial_state)

        return ShoppingGuideChatResponse(
            session_id=request.session_id,
            agent_task_id=final_state.get("agent_task_id"),
            intent=final_state.get("intent") or "shopping_guide",
            answer=final_state.get("answer") or "我暂时没有找到合适推荐，请补充预算、使用场景或偏好。",
            budget=final_state.get("budget"),
            scenario=final_state.get("scenario"),
            preferences=final_state.get("preferences") or [],
            recommendations=final_state.get("recommendations") or [],
            comparisons=final_state.get("comparisons") or [],
            tool_calls=final_state.get("tool_calls") or [],
            citations=final_state.get("citations") or [],
            metadata=final_state.get("metadata") or {},
        )