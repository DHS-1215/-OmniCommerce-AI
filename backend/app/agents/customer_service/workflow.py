# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/05/02 22:18
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from typing import Any

from langgraph.graph import END, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.customer_service.intents import CustomerServiceIntent
from app.agents.customer_service.nodes import (
    aftersale_tool_node,
    create_agent_task_node,
    finalize_task_node,
    generate_answer_node,
    handoff_tool_node,
    identify_intent_node,
    order_tool_node,
    policy_rag_node,
    product_tool_node,
    validate_result_node,
)
from app.agents.customer_service.state import CustomerServiceAgentState
from app.services.agent_step_log_service import AgentStepLogService
from app.services.agent_task_service import AgentTaskService
from app.services.tool_call_log_service import ToolCallLogService
from app.tools.aftersale_tools import AftersaleTools
from app.tools.knowledge_tools import KnowledgeTools
from app.tools.order_tools import OrderTools
from app.tools.product_tools import ProductTools
from app.tools.ticket_tools import TicketTools


def route_by_intent(state: CustomerServiceAgentState) -> str:
    """根据客服意图路由到对应工具节点。"""

    if state.get("handoff_required"):
        return "handoff"

    intent = state.get("intent") or CustomerServiceIntent.UNKNOWN.value

    if intent == CustomerServiceIntent.PRODUCT_QUERY:
        return "product"

    if intent == CustomerServiceIntent.ORDER_QUERY:
        return "order"

    if intent in {
        CustomerServiceIntent.AFTERSALE_APPLY,
        CustomerServiceIntent.AFTERSALE_QUERY,
    }:
        return "aftersale"

    if intent == CustomerServiceIntent.POLICY_QUERY:
        return "policy"

    if intent in {
        CustomerServiceIntent.COMPLAINT,
        CustomerServiceIntent.HUMAN_HANDOFF,
    }:
        return "handoff"

    return "no_tool"


def route_after_validate(state: CustomerServiceAgentState) -> str:
    """校验后判断是否需要创建人工工单。"""

    if not state.get("handoff_required"):
        return "generate_answer"

    metadata = state.get("metadata") or {}
    if metadata.get("handoff_ticket_created"):
        return "generate_answer"

    return "handoff"


def passthrough_node(state: CustomerServiceAgentState) -> CustomerServiceAgentState:
    """无需工具调用的普通节点。"""

    return state


def build_customer_service_workflow(
        *,
        db: AsyncSession,
        prompt_service: Any,
        model_gateway: Any,
        agent_task_service: AgentTaskService,
        step_log_service: AgentStepLogService,
        tool_call_log_service: ToolCallLogService,
        product_tools: ProductTools,
        order_tools: OrderTools,
        aftersale_tools: AftersaleTools,
        ticket_tools: TicketTools,
        knowledge_tools: KnowledgeTools,
):
    """构建智能客服 LangGraph 工作流。

    工作流职责：
    - 创建 Agent 任务；
    - 识别用户意图；
    - 根据意图路由到业务工具 / RAG / 转人工；
    - 校验工具结果与高风险策略；
    - 生成最终回答；
    - 收尾 Agent 任务。

    注意：
    - 本函数只做编排；
    - 具体业务能力在 tools / services；
    - 模型调用在 ModelGateway；
    - Prompt 渲染在 PromptService。
    """

    graph = StateGraph(CustomerServiceAgentState)

    async def create_task(state: CustomerServiceAgentState) -> CustomerServiceAgentState:
        return await create_agent_task_node(
            state,
            agent_task_service=agent_task_service,
        )

    async def identify_intent(state: CustomerServiceAgentState) -> CustomerServiceAgentState:
        return await identify_intent_node(
            state,
            db=db,
            prompt_service=prompt_service,
            model_gateway=model_gateway,
        )

    async def product_tool(state: CustomerServiceAgentState) -> CustomerServiceAgentState:
        return await product_tool_node(
            state,
            product_tools=product_tools,
            step_log_service=step_log_service,
            tool_call_log_service=tool_call_log_service,
        )

    async def order_tool(state: CustomerServiceAgentState) -> CustomerServiceAgentState:
        return await order_tool_node(
            state,
            order_tools=order_tools,
            step_log_service=step_log_service,
            tool_call_log_service=tool_call_log_service,
        )

    async def aftersale_tool(state: CustomerServiceAgentState) -> CustomerServiceAgentState:
        return await aftersale_tool_node(
            state,
            aftersale_tools=aftersale_tools,
            step_log_service=step_log_service,
            tool_call_log_service=tool_call_log_service,
        )

    async def policy_tool(state: CustomerServiceAgentState) -> CustomerServiceAgentState:
        return await policy_rag_node(
            state,
            knowledge_tools=knowledge_tools,
            step_log_service=step_log_service,
            tool_call_log_service=tool_call_log_service,
        )

    async def handoff_tool(state: CustomerServiceAgentState) -> CustomerServiceAgentState:
        return await handoff_tool_node(
            state,
            ticket_tools=ticket_tools,
            step_log_service=step_log_service,
            tool_call_log_service=tool_call_log_service,
        )

    async def validate_result(state: CustomerServiceAgentState) -> CustomerServiceAgentState:
        return await validate_result_node(
            state,
            step_log_service=step_log_service,
        )

    async def generate_answer(state: CustomerServiceAgentState) -> CustomerServiceAgentState:
        return await generate_answer_node(
            state,
            db=db,
            prompt_service=prompt_service,
            model_gateway=model_gateway,
            step_log_service=step_log_service,
        )

    async def finalize_task(state: CustomerServiceAgentState) -> CustomerServiceAgentState:
        return await finalize_task_node(
            state,
            agent_task_service=agent_task_service,
        )

    graph.add_node("create_task", create_task)
    graph.add_node("identify_intent", identify_intent)
    graph.add_node("product_tool", product_tool)
    graph.add_node("order_tool", order_tool)
    graph.add_node("aftersale_tool", aftersale_tool)
    graph.add_node("policy_tool", policy_tool)
    graph.add_node("handoff_tool", handoff_tool)
    graph.add_node("no_tool", passthrough_node)
    graph.add_node("validate_result", validate_result)
    graph.add_node("generate_answer", generate_answer)
    graph.add_node("finalize_task", finalize_task)

    graph.set_entry_point("create_task")

    graph.add_edge("create_task", "identify_intent")

    graph.add_conditional_edges(
        "identify_intent",
        route_by_intent,
        {
            "product": "product_tool",
            "order": "order_tool",
            "aftersale": "aftersale_tool",
            "policy": "policy_tool",
            "handoff": "handoff_tool",
            "no_tool": "no_tool",
        },
    )

    graph.add_edge("product_tool", "validate_result")
    graph.add_edge("order_tool", "validate_result")
    graph.add_edge("aftersale_tool", "validate_result")
    graph.add_edge("policy_tool", "validate_result")
    graph.add_edge("no_tool", "validate_result")

    # 直接进入 handoff_tool 的场景，已经创建过工单，不需要再 validate 后重复创建。
    graph.add_edge("handoff_tool", "generate_answer")

    graph.add_conditional_edges(
        "validate_result",
        route_after_validate,
        {
            "handoff": "handoff_tool",
            "generate_answer": "generate_answer",
        },
    )

    graph.add_edge("generate_answer", "finalize_task")
    graph.add_edge("finalize_task", END)

    return graph.compile()
