# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/05/02 22:23
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.customer_service.workflow import build_customer_service_workflow
from app.llm.gateway import build_model_gateway
from app.schemas.agent import (
    AgentCitationView,
    AgentToolCallView,
    CustomerServiceChatRequest,
    CustomerServiceChatResponse,
)
from app.services.aftersale_service import AfterSaleService
from app.services.agent_step_log_service import AgentStepLogService
from app.services.agent_task_service import AgentTaskService
from app.services.knowledge_service import KnowledgeService
from app.services.model_call_log_service import ModelCallLogService
from app.services.order_service import OrderService
from app.services.product_service import ProductService
from app.services.prompt_service import PromptService
from app.services.ticket_service import CustomerServiceTicketService
from app.services.tool_call_log_service import ToolCallLogService
from app.tools.aftersale_tools import AftersaleTools
from app.tools.knowledge_tools import KnowledgeTools
from app.tools.order_tools import OrderTools
from app.tools.product_tools import ProductTools
from app.tools.ticket_tools import TicketTools


class CustomerServiceAgentService:
    """智能客服 Agent 服务。

    职责：
    - 组装 PromptService / ModelGateway / Tools / LogServices；
    - 构建并执行 LangGraph 工作流；
    - 将 AgentState 转换为 API 响应 schema。

    不做：
    - 不直接查数据库；
    - 不直接调用外部模型 API；
    - 不在 API 层暴露 LangGraph 内部状态。
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def chat(
            self,
            *,
            request: CustomerServiceChatRequest,
            request_id: str | None = None,
    ) -> CustomerServiceChatResponse:
        prompt_service = PromptService()

        model_call_log_service = ModelCallLogService(self.db)
        model_gateway = build_model_gateway(model_call_log_service)

        agent_task_service = AgentTaskService(self.db)
        step_log_service = AgentStepLogService(self.db)
        tool_call_log_service = ToolCallLogService(self.db)

        product_tools = ProductTools(
            db=self.db,
            product_service=ProductService(),
        )
        order_tools = OrderTools(
            db=self.db,
            order_service=OrderService(),
        )
        aftersale_tools = AftersaleTools(
            db=self.db,
            aftersale_service=AfterSaleService(),
        )
        ticket_tools = TicketTools(
            db=self.db,
            ticket_service=CustomerServiceTicketService(),
        )
        knowledge_tools = KnowledgeTools(
            db=self.db,
            knowledge_service=KnowledgeService(),
        )

        workflow = build_customer_service_workflow(
            db=self.db,
            prompt_service=prompt_service,
            model_gateway=model_gateway,
            agent_task_service=agent_task_service,
            step_log_service=step_log_service,
            tool_call_log_service=tool_call_log_service,
            product_tools=product_tools,
            order_tools=order_tools,
            aftersale_tools=aftersale_tools,
            ticket_tools=ticket_tools,
            knowledge_tools=knowledge_tools,
        )

        initial_state: dict[str, Any] = {
            "tenant_id": request.tenant_id,
            "user_id": request.user_id,
            "user_no": request.user_no,
            "session_id": request.session_id,
            "request_id": request_id,
            "message": request.message,
            "conversation_summary": request.conversation_summary,
            "context": request.context or {},
            "agent_task_id": None,
            "intent": None,
            "confidence": None,
            "entities": {},
            "selected_tools": [],
            "tool_results": [],
            "rag_answer": None,
            "citations": [],
            "answer": None,
            "handoff_required": False,
            "handoff_reason": None,
            "error_code": None,
            "error_message": None,
            "metadata": {},
        }

        final_state = await workflow.ainvoke(initial_state)

        return self._build_response(
            request=request,
            state=final_state,
        )

    def _build_response(
            self,
            *,
            request: CustomerServiceChatRequest,
            state: dict[str, Any],
    ) -> CustomerServiceChatResponse:
        tool_calls = [
            AgentToolCallView(
                tool_name=item.get("tool_name") or "",
                success=bool(item.get("success")),
                error_code=item.get("error_code"),
                error_message=item.get("error_message"),
            )
            for item in state.get("tool_results") or []
        ]

        citations = [
            AgentCitationView(**item)
            for item in state.get("citations") or []
            if isinstance(item, dict)
        ]

        return CustomerServiceChatResponse(
            session_id=request.session_id,
            agent_task_id=state.get("agent_task_id"),
            intent=state.get("intent") or "unknown",
            answer=state.get("answer") or "我已收到你的问题，但暂时无法生成完整回复。",
            handoff_required=bool(state.get("handoff_required")),
            handoff_reason=state.get("handoff_reason"),
            tool_calls=tool_calls,
            citations=citations,
            steps=[],
            metadata=state.get("metadata") or {},
        )
