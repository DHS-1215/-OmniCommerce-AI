# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/05/02 20:38
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
import time
import json
import re
from typing import Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from collections.abc import Awaitable, Callable

from app.llm.schemas import ChatRequest, LLMMessage
from app.schemas.prompt import PromptRenderRequest

from app.agents.customer_service.policies import (
    is_high_risk_message,
    is_human_handoff_requested,
    should_handoff,
)
from app.agents.customer_service.state import CustomerServiceAgentState
from app.core.exceptions import BaseAppException

from app.services.agent_task_service import AgentTaskService
from app.services.agent_step_log_service import AgentStepLogService
from app.tools.base import ToolResult, summarize_value, tool_result_to_log_summary

from app.services.tool_call_log_service import ToolCallLogService

from app.tools.order_tools import OrderTools
from app.tools.product_tools import ProductTools

from app.agents.customer_service.intents import CustomerServiceIntent, normalize_intent
from app.schemas.aftersale import AfterSaleCreateRequest
from app.tools.aftersale_tools import AftersaleTools

from app.tools.knowledge_tools import KnowledgeTools

from app.schemas.ticket import CustomerServiceTicketCreateRequest
from app.tools.ticket_tools import TicketTools

ORDER_NO_PATTERN = re.compile(r"\bO\d{6,}\b", re.IGNORECASE)
PRODUCT_NO_PATTERN = re.compile(r"\bP\d{6,}\b", re.IGNORECASE)
SKU_NO_PATTERN = re.compile(r"\bSKU\d{6,}\b", re.IGNORECASE)
AFTERSALE_TICKET_NO_PATTERN = re.compile(r"\bAS\d{6,}\b", re.IGNORECASE)

PRODUCT_KEYWORDS = [
    "商品",
    "产品",
    "价格",
    "多少钱",
    "库存",
    "规格",
    "sku",
    "评价",
    "好用吗",
    "质量",
    "颜色",
    "型号",
]

ORDER_KEYWORDS = [
    "订单",
    "发货",
    "物流",
    "快递",
    "到哪",
    "送达",
    "支付",
    "付款",
    "什么时候到",
    "什么时候发",
]

AFTERSALE_APPLY_KEYWORDS = [
    "退款",
    "退货",
    "换货",
    "申请售后",
    "我要退",
    "我要换",
    "不想要了",
    "坏了",
    "破损",
]

AFTERSALE_QUERY_KEYWORDS = [
    "售后进度",
    "售后单",
    "退款进度",
    "退货进度",
    "审核到哪",
]

POLICY_KEYWORDS = [
    "政策",
    "规则",
    "七天无理由",
    "无理由退货",
    "退货条件",
    "退款条件",
    "售后规则",
    "保修",
    "赔付规则",
]


def _safe_get_message(state: CustomerServiceAgentState) -> str:
    return str(state.get("message") or "").strip()


def _extract_first(pattern: re.Pattern[str], text: str) -> str | None:
    match = pattern.search(text)
    if not match:
        return None
    return match.group(0).upper()


def extract_entities(message: str) -> dict[str, Any]:
    """从用户输入中用规则抽取基础业务实体。

    第一版只抽取常见业务编号：
    - order_no
    - product_no
    - sku_no
    - after_sale_ticket_no

    复杂实体抽取后续可以交给 Prompt 或专门 NLU 节点增强。
    """

    return {
        "order_no": _extract_first(ORDER_NO_PATTERN, message),
        "product_no": _extract_first(PRODUCT_NO_PATTERN, message),
        "sku_no": _extract_first(SKU_NO_PATTERN, message),
        "after_sale_ticket_no": _extract_first(AFTERSALE_TICKET_NO_PATTERN, message),
    }


def _contains_any(text: str, keywords: list[str]) -> bool:
    lowered = text.lower()
    return any(keyword.lower() in lowered for keyword in keywords)


def rule_based_intent(message: str) -> tuple[CustomerServiceIntent, float, str]:
    """规则兜底意图识别。

    用于：
    - Mock Provider 输出不稳定；
    - 模型返回非 JSON；
    - 模型调用失败；
    - 低成本本地测试。
    """

    if not message:
        return CustomerServiceIntent.UNKNOWN, 0.0, "empty_message"

    if is_human_handoff_requested(message):
        return CustomerServiceIntent.HUMAN_HANDOFF, 0.95, "human_handoff_keyword"

    if is_high_risk_message(message):
        return CustomerServiceIntent.COMPLAINT, 0.95, "high_risk_keyword"

    if _contains_any(message, POLICY_KEYWORDS):
        return CustomerServiceIntent.POLICY_QUERY, 0.85, "policy_keyword"

    if _contains_any(message, AFTERSALE_QUERY_KEYWORDS):
        return CustomerServiceIntent.AFTERSALE_QUERY, 0.85, "aftersale_query_keyword"

    if _contains_any(message, AFTERSALE_APPLY_KEYWORDS):
        return CustomerServiceIntent.AFTERSALE_APPLY, 0.82, "aftersale_apply_keyword"

    if _extract_first(ORDER_NO_PATTERN, message) or _contains_any(message, ORDER_KEYWORDS):
        return CustomerServiceIntent.ORDER_QUERY, 0.82, "order_keyword_or_order_no"

    if (
            _extract_first(PRODUCT_NO_PATTERN, message)
            or _extract_first(SKU_NO_PATTERN, message)
            or _contains_any(message, PRODUCT_KEYWORDS)
    ):
        return CustomerServiceIntent.PRODUCT_QUERY, 0.78, "product_keyword_or_product_no"

    return CustomerServiceIntent.GENERAL_CHAT, 0.55, "general_fallback"


def guarded_rule_based_intent(
        *,
        message: str,
        context: dict[str, Any],
        extracted_entities: dict[str, Any],
) -> tuple[CustomerServiceIntent, float, str, bool, str | None]:
    """高优先级意图保护规则。

    用于覆盖 LLM 明显误判的场景：
    - 用户明确要求人工；
    - 投诉、赔付、曝光等高风险；
    - context / entities 里已有明确 product_no / sku_no；
    - context / entities 里已有明确售后单号；
    - context / entities 里已有明确订单号。
    """

    if is_human_handoff_requested(message):
        return (
            CustomerServiceIntent.HUMAN_HANDOFF,
            0.98,
            "guard_human_handoff_keyword",
            True,
            "用户明确要求人工客服",
        )

    if is_high_risk_message(message):
        return (
            CustomerServiceIntent.COMPLAINT,
            0.98,
            "guard_high_risk_keyword",
            True,
            "用户表达涉及投诉、赔付、曝光等高风险诉求",
        )

    product_no = extracted_entities.get("product_no") or context.get("product_no")
    sku_no = extracted_entities.get("sku_no") or context.get("sku_no")
    if product_no or sku_no:
        return (
            CustomerServiceIntent.PRODUCT_QUERY,
            0.93,
            "guard_product_context",
            False,
            None,
        )

    after_sale_ticket_no = (
            extracted_entities.get("after_sale_ticket_no")
            or context.get("after_sale_ticket_no")
            or context.get("ticket_no")
    )
    if after_sale_ticket_no:
        return (
            CustomerServiceIntent.AFTERSALE_QUERY,
            0.93,
            "guard_aftersale_ticket_context",
            False,
            None,
        )

    rule_intent, rule_confidence, rule_reason = rule_based_intent(message)

    if rule_confidence >= 0.8 and rule_intent not in {
        CustomerServiceIntent.UNKNOWN,
        CustomerServiceIntent.GENERAL_CHAT,
    }:
        need_handoff = rule_intent in {
            CustomerServiceIntent.COMPLAINT,
            CustomerServiceIntent.HUMAN_HANDOFF,
        }
        handoff_reason = None
        if rule_intent == CustomerServiceIntent.COMPLAINT:
            handoff_reason = "用户表达涉及投诉、赔付、曝光等高风险诉求"
        elif rule_intent == CustomerServiceIntent.HUMAN_HANDOFF:
            handoff_reason = "用户明确要求人工客服"

        return (
            rule_intent,
            rule_confidence,
            rule_reason,
            need_handoff,
            handoff_reason,
        )

    return CustomerServiceIntent.UNKNOWN, 0.0, "guard_no_match", False, None


def _extract_json_object(text: str) -> dict[str, Any] | None:
    """尽量从模型输出中提取 JSON 对象。

    兼容这些情况：
    - 纯 JSON；
    - Markdown ```json 代码块；
    - 前后有解释文字，中间夹一个 JSON object。
    """

    if not text:
        return None

    cleaned = text.strip()

    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = cleaned.removeprefix("json").strip()

    try:
        value = json.loads(cleaned)
        if isinstance(value, dict):
            return value
    except json.JSONDecodeError:
        pass

    start = cleaned.find("{")
    end = cleaned.rfind("}")

    if start >= 0 and end > start:
        candidate = cleaned[start: end + 1]
        try:
            value = json.loads(candidate)
            if isinstance(value, dict):
                return value
        except json.JSONDecodeError:
            return None

    return None


def parse_llm_intent_response(content: str) -> tuple[CustomerServiceIntent, float, dict[str, Any], bool, str | None]:
    """解析模型意图识别结果。

    期望模型返回：
    {
      "intent": "order_query",
      "confidence": 0.86,
      "entities": {"order_no": "O100001"},
      "need_handoff": false,
      "reason": ""
    }
    """

    payload = _extract_json_object(content)

    if not payload:
        return CustomerServiceIntent.UNKNOWN, 0.0, {}, False, "模型输出不是可解析 JSON"

    intent = normalize_intent(str(payload.get("intent") or "unknown"))

    try:
        confidence = float(payload.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0

    entities = payload.get("entities") or {}
    if not isinstance(entities, dict):
        entities = {}

    need_handoff = bool(payload.get("need_handoff", False))
    reason = payload.get("reason")
    reason = str(reason) if reason else None

    return intent, confidence, entities, need_handoff, reason


async def identify_intent_node(
        state: CustomerServiceAgentState,
        *,
        db: AsyncSession,
        prompt_service: Any,
        model_gateway: Any,
) -> CustomerServiceAgentState:
    """客服意图识别节点。

    正常路径：
    - 从 Prompt 管理读取 customer_service_intent；
    - 渲染 Prompt；
    - 调用 ModelGateway.chat；
    - 解析 JSON。

    兜底路径：
    - Prompt 渲染失败；
    - 模型调用失败；
    - 模型输出不可解析；
    - 使用规则识别。
    """

    message = _safe_get_message(state)
    conversation_summary = state.get("conversation_summary") or ""
    context = state.get("context") or {}

    extracted_entities = extract_entities(message)

    try:
        rendered_prompt = await prompt_service.render_prompt(
            db,
            payload=PromptRenderRequest(
                tenant_id=state["tenant_id"],
                scene="customer_service_intent",
                variables={
                    "user_message": message,
                    "conversation_summary": conversation_summary,
                    "context": context,
                },
            ),
        )

        model_config = rendered_prompt.model_config_json or {}
        provider = model_config.get("provider")
        model = model_config.get("model")

        model_response = await model_gateway.chat(
            ChatRequest(
                tenant_id=state["tenant_id"],
                request_id=state.get("request_id"),
                user_id=state.get("user_id"),
                provider=provider,
                model=model,
                prompt_template_id=rendered_prompt.template_id,
                prompt_version_id=rendered_prompt.version_id,
                messages=[
                    LLMMessage(
                        role="user",
                        content=rendered_prompt.rendered_content,
                    )
                ],
            )
        )

        content = model_response.content or ""

        intent, confidence, llm_entities, need_handoff, reason = parse_llm_intent_response(
            content
        )

        guard_intent, guard_confidence, guard_reason, guard_handoff, guard_handoff_reason = (
            guarded_rule_based_intent(
                message=message,
                context=context,
                extracted_entities={
                    **extracted_entities,
                    **llm_entities,
                },
            )
        )

        if guard_intent != CustomerServiceIntent.UNKNOWN:
            intent = guard_intent
            confidence = max(confidence, guard_confidence)
            need_handoff = guard_handoff
            reason = guard_handoff_reason
            intent_source = "rule_guard"
        else:
            intent_source = "llm"

        if intent == CustomerServiceIntent.UNKNOWN:
            fallback_intent, fallback_confidence, fallback_reason, fallback_handoff, fallback_handoff_reason = (
                guarded_rule_based_intent(
                    message=message,
                    context=context,
                    extracted_entities={
                        **extracted_entities,
                        **llm_entities,
                    },
                )
            )

            if fallback_intent == CustomerServiceIntent.UNKNOWN:
                fallback_intent, fallback_confidence, fallback_reason = rule_based_intent(message)
                fallback_handoff = fallback_intent in {
                    CustomerServiceIntent.COMPLAINT,
                    CustomerServiceIntent.HUMAN_HANDOFF,
                }
                fallback_handoff_reason = None
                state["handoff_required"] = fallback_handoff
                state["handoff_reason"] = fallback_handoff_reason if fallback_handoff else None

            state["intent"] = fallback_intent.value
            state["confidence"] = fallback_confidence
            state["entities"] = {
                **extracted_entities,
                **llm_entities,
            }
            state["metadata"] = {
                **(state.get("metadata") or {}),
                "intent_source": "rule_fallback",
                "intent_reason": fallback_reason,
                "llm_parse_error": reason,
                "prompt_template_id": str(rendered_prompt.template_id),
                "prompt_version_id": str(rendered_prompt.version_id),
            }
            return state

        state["intent"] = intent.value
        state["confidence"] = confidence
        state["entities"] = {
            **extracted_entities,
            **llm_entities,
        }
        state["handoff_required"] = need_handoff
        state["handoff_reason"] = reason if need_handoff else None
        state["metadata"] = {
            **(state.get("metadata") or {}),
            "intent_source": intent_source,
            "intent_guard_reason": guard_reason,
            "prompt_template_id": str(rendered_prompt.template_id),
            "prompt_version_id": str(rendered_prompt.version_id),
        }
        return state

    except BaseAppException as exc:
        fallback_intent, fallback_confidence, fallback_reason = rule_based_intent(message)

        state["intent"] = fallback_intent.value
        state["confidence"] = fallback_confidence
        state["entities"] = extracted_entities
        state["metadata"] = {
            **(state.get("metadata") or {}),
            "intent_source": "rule_fallback",
            "intent_reason": fallback_reason,
            "fallback_cause": getattr(exc, "code", "BUSINESS_ERROR"),
        }
        return state

    except Exception as exc:
        fallback_intent, fallback_confidence, fallback_reason = rule_based_intent(message)

        state["intent"] = fallback_intent.value
        state["confidence"] = fallback_confidence
        state["entities"] = extracted_entities
        state["metadata"] = {
            **(state.get("metadata") or {}),
            "intent_source": "rule_fallback",
            "intent_reason": fallback_reason,
            "fallback_cause": exc.__class__.__name__,
        }
        return state


def _state_summary(state: CustomerServiceAgentState, max_length: int = 500) -> str:
    """生成 Agent 状态摘要，用于 agent_task / step_log。"""

    payload = {
        "session_id": state.get("session_id"),
        "user_no": state.get("user_no"),
        "message": state.get("message"),
        "intent": state.get("intent"),
        "confidence": state.get("confidence"),
        "handoff_required": state.get("handoff_required"),
        "handoff_reason": state.get("handoff_reason"),
    }
    return summarize_value(payload, max_length=max_length)


async def create_agent_task_node(
        state: CustomerServiceAgentState,
        *,
        agent_task_service: AgentTaskService,
) -> CustomerServiceAgentState:
    """创建 Agent 任务记录。"""

    task = await agent_task_service.create_task(
        tenant_id=state["tenant_id"],
        agent_type="customer_service",
        session_id=state["session_id"],
        input_summary=_state_summary(state),
        request_id=state.get("request_id"),
        user_id=state.get("user_id"),
        intent=state.get("intent"),
    )

    state["agent_task_id"] = task.id
    state["metadata"] = {
        **(state.get("metadata") or {}),
        "agent_task_no": task.task_no,
    }
    return state


async def log_step_start(
        state: CustomerServiceAgentState,
        *,
        step_log_service: AgentStepLogService,
        step_name: str,
        step_order: int,
) -> tuple[Any, float]:
    """创建步骤日志并返回 step_log 与开始时间。"""

    if not state.get("agent_task_id"):
        raise ValueError("agent_task_id is required before logging steps")

    start = time.perf_counter()

    step = await step_log_service.create_step(
        tenant_id=state["tenant_id"],
        agent_task_id=state["agent_task_id"],
        step_name=step_name,
        step_order=step_order,
        input_summary=_state_summary(state),
        request_id=state.get("request_id"),
        status="running",
    )

    return step, start


async def log_step_success(
        state: CustomerServiceAgentState,
        *,
        step_log_service: AgentStepLogService,
        step: Any,
        start: float,
        output_summary: str | None = None,
) -> None:
    """标记步骤成功。"""

    latency_ms = int((time.perf_counter() - start) * 1000)
    await step_log_service.mark_success(
        step=step,
        output_summary=output_summary or _state_summary(state),
        latency_ms=latency_ms,
    )


async def log_step_failed(
        *,
        step_log_service: AgentStepLogService,
        step: Any,
        start: float,
        error_message: str,
) -> None:
    """标记步骤失败。"""

    latency_ms = int((time.perf_counter() - start) * 1000)
    await step_log_service.mark_failed(
        step=step,
        error_message=error_message,
        latency_ms=latency_ms,
    )


async def finalize_task_node(
        state: CustomerServiceAgentState,
        *,
        agent_task_service: AgentTaskService,
) -> CustomerServiceAgentState:
    """收尾 Agent 任务。"""

    agent_task_id = state.get("agent_task_id")
    if not agent_task_id:
        return state

    task = await agent_task_service.get_by_id(
        tenant_id=state["tenant_id"],
        task_id=agent_task_id,
    )
    if task is None:
        state["metadata"] = {
            **(state.get("metadata") or {}),
            "finalize_error": "agent_task_not_found",
        }
        return state

    if state.get("error_code") or state.get("error_message"):
        await agent_task_service.mark_failed(
            task=task,
            error_message=state.get("error_message") or state.get("error_code"),
            intent=state.get("intent"),
        )
        return state

    if state.get("handoff_required"):
        await agent_task_service.mark_handoff_required(
            task=task,
            reason=state.get("handoff_reason") or "需要人工客服处理",
            intent=state.get("intent"),
            output_summary=state.get("answer"),
        )
        return state

    await agent_task_service.mark_success(
        task=task,
        output_summary=state.get("answer"),
        intent=state.get("intent"),
        handoff_required=False,
    )
    return state


def _guess_aftersale_type(message: str | None) -> str:
    """根据用户文本粗略判断售后类型。

    第一版只做轻量规则：
    - 换货类表达 -> exchange
    - 退货类表达 -> return
    - 默认退款 -> refund
    """

    if not message:
        return "refund"

    if _contains_any(message, ["换货", "换一个", "更换"]):
        return "exchange"

    if _contains_any(message, ["退货", "我要退", "不想要了"]):
        return "return"

    return "refund"


async def call_tool_with_log(
        state: CustomerServiceAgentState,
        *,
        tool_call_log_service: ToolCallLogService,
        tool_name: str,
        tool_type: str,
        tool_input: dict[str, Any],
        tool_func: Callable[[], Awaitable[ToolResult]],
        agent_step_log_id: UUID | None = None,
) -> ToolResult:
    """调用工具并写入 tool_call_log。

    这个 helper 统一处理：
    - 工具耗时；
    - 成功 / 失败状态；
    - 入参摘要；
    - 出参摘要；
    - tool_results 写回 state。

    注意：
    - tool_func 必须返回 ToolResult；
    - 工具内部仍然只调用 service 层；
    - 这里不直接查数据库。
    """

    if not state.get("agent_task_id"):
        raise ValueError("agent_task_id is required before calling tools")

    start = time.perf_counter()

    try:
        result = await tool_func()
    except Exception as exc:
        result = ToolResult.fail(
            tool_name=tool_name,
            error_code="AGENT_TOOL_CALL_FAILED",
            error_message=f"{tool_name} 执行失败：{exc.__class__.__name__}",
        )

    latency_ms = int((time.perf_counter() - start) * 1000)

    await tool_call_log_service.create_tool_call_log(
        tenant_id=state["tenant_id"],
        request_id=state.get("request_id"),
        agent_task_id=state["agent_task_id"],
        agent_step_log_id=agent_step_log_id,
        tool_name=result.tool_name or tool_name,
        tool_type=tool_type,
        input_summary=summarize_value(tool_input),
        output_summary=tool_result_to_log_summary(result),
        status="success" if result.success else "failed",
        latency_ms=latency_ms,
        error_code=result.error_code,
        error_message=result.error_message,
    )

    tool_results = list(state.get("tool_results") or [])
    tool_results.append(
        {
            "success": result.success,
            "tool_name": result.tool_name,
            "data": result.data,
            "error_code": result.error_code,
            "error_message": result.error_message,
            "latency_ms": latency_ms,
        }
    )
    state["tool_results"] = tool_results

    return result


async def order_tool_node(
        state: CustomerServiceAgentState,
        *,
        order_tools: OrderTools,
        step_log_service: AgentStepLogService,
        tool_call_log_service: ToolCallLogService,
) -> CustomerServiceAgentState:
    """订单查询工具节点。

    支持：
    - 已有 order_no：查询订单详情；
    - 没有 order_no 但有 user_no：查询用户订单列表；
    - 两者都没有：不调用工具，后续生成追问。
    """

    step, start = await log_step_start(
        state,
        step_log_service=step_log_service,
        step_name="order_tool_node",
        step_order=30,
    )

    try:
        context = state.get("context") or {}
        entities = state.get("entities") or {}

        order_no = (
                entities.get("order_no")
                or context.get("order_no")
        )
        user_no = state.get("user_no") or context.get("user_no")

        if order_no:
            tool_input = {
                "tenant_id": str(state["tenant_id"]),
                "order_no": order_no,
            }

            result = await call_tool_with_log(
                state,
                tool_call_log_service=tool_call_log_service,
                tool_name="get_order_detail",
                tool_type="order",
                tool_input=tool_input,
                agent_step_log_id=step.id,
                tool_func=lambda: order_tools.get_order_detail(
                    tenant_id=state["tenant_id"],
                    order_no=order_no,
                ),
            )

            if result.success:
                state["metadata"] = {
                    **(state.get("metadata") or {}),
                    "order_query_mode": "detail",
                    "order_no": order_no,
                }
            else:
                state["error_code"] = result.error_code
                state["error_message"] = result.error_message

            await log_step_success(
                state,
                step_log_service=step_log_service,
                step=step,
                start=start,
                output_summary=summarize_value(
                    {
                        "mode": "detail",
                        "order_no": order_no,
                        "success": result.success,
                        "error_code": result.error_code,
                    }
                ),
            )
            return state

        if user_no:
            tool_input = {
                "tenant_id": str(state["tenant_id"]),
                "user_no": user_no,
                "page": 1,
                "page_size": 5,
            }

            result = await call_tool_with_log(
                state,
                tool_call_log_service=tool_call_log_service,
                tool_name="list_orders",
                tool_type="order",
                tool_input=tool_input,
                agent_step_log_id=step.id,
                tool_func=lambda: order_tools.list_orders(
                    tenant_id=state["tenant_id"],
                    user_no=user_no,
                    page=1,
                    page_size=5,
                ),
            )

            if result.success:
                state["metadata"] = {
                    **(state.get("metadata") or {}),
                    "order_query_mode": "list",
                    "user_no": user_no,
                }
            else:
                state["error_code"] = result.error_code
                state["error_message"] = result.error_message

            await log_step_success(
                state,
                step_log_service=step_log_service,
                step=step,
                start=start,
                output_summary=summarize_value(
                    {
                        "mode": "list",
                        "user_no": user_no,
                        "success": result.success,
                        "error_code": result.error_code,
                    }
                ),
            )
            return state

        state["handoff_required"] = False
        state["metadata"] = {
            **(state.get("metadata") or {}),
            "order_query_mode": "need_more_info",
            "missing_fields": ["order_no"],
        }

        await log_step_success(
            state,
            step_log_service=step_log_service,
            step=step,
            start=start,
            output_summary="订单查询缺少 order_no，后续需要追问用户",
        )
        return state

    except Exception as exc:
        state["error_code"] = "ORDER_TOOL_NODE_FAILED"
        state["error_message"] = f"订单工具节点执行失败：{exc.__class__.__name__}"

        await log_step_failed(
            step_log_service=step_log_service,
            step=step,
            start=start,
            error_message=state["error_message"],
        )
        return state


async def product_tool_node(
        state: CustomerServiceAgentState,
        *,
        product_tools: ProductTools,
        step_log_service: AgentStepLogService,
        tool_call_log_service: ToolCallLogService,
) -> CustomerServiceAgentState:
    """商品咨询工具节点。

    支持：
    - sku_no：查 SKU 详情；
    - product_no：查商品详情和 SKU 列表；
    - 评价类问题：查商品评价；
    - 无明确编号：按用户输入 keyword 查商品列表。
    """

    step, start = await log_step_start(
        state,
        step_log_service=step_log_service,
        step_name="product_tool_node",
        step_order=30,
    )

    try:
        message = _safe_get_message(state)
        context = state.get("context") or {}
        entities = state.get("entities") or {}

        product_no = entities.get("product_no") or context.get("product_no")
        sku_no = entities.get("sku_no") or context.get("sku_no")

        wants_reviews = _contains_any(
            message,
            [
                "评价",
                "评论",
                "好用吗",
                "质量",
                "口碑",
                "差评",
                "好评",
            ],
        )

        if sku_no:
            tool_input = {
                "tenant_id": str(state["tenant_id"]),
                "sku_no": sku_no,
            }

            result = await call_tool_with_log(
                state,
                tool_call_log_service=tool_call_log_service,
                tool_name="get_sku_detail",
                tool_type="product",
                tool_input=tool_input,
                agent_step_log_id=step.id,
                tool_func=lambda: product_tools.get_sku_detail(
                    tenant_id=state["tenant_id"],
                    sku_no=sku_no,
                ),
            )

            if not result.success:
                state["error_code"] = result.error_code
                state["error_message"] = result.error_message

            await log_step_success(
                state,
                step_log_service=step_log_service,
                step=step,
                start=start,
                output_summary=summarize_value(
                    {
                        "mode": "sku_detail",
                        "sku_no": sku_no,
                        "success": result.success,
                        "error_code": result.error_code,
                    }
                ),
            )
            return state

        if product_no:
            detail_input = {
                "tenant_id": str(state["tenant_id"]),
                "product_no": product_no,
            }

            detail_result = await call_tool_with_log(
                state,
                tool_call_log_service=tool_call_log_service,
                tool_name="get_product_detail",
                tool_type="product",
                tool_input=detail_input,
                agent_step_log_id=step.id,
                tool_func=lambda: product_tools.get_product_detail(
                    tenant_id=state["tenant_id"],
                    product_no=product_no,
                ),
            )

            sku_result = await call_tool_with_log(
                state,
                tool_call_log_service=tool_call_log_service,
                tool_name="list_product_skus",
                tool_type="product",
                tool_input=detail_input,
                agent_step_log_id=step.id,
                tool_func=lambda: product_tools.list_product_skus(
                    tenant_id=state["tenant_id"],
                    product_no=product_no,
                ),
            )

            if wants_reviews:
                await call_tool_with_log(
                    state,
                    tool_call_log_service=tool_call_log_service,
                    tool_name="list_product_reviews",
                    tool_type="product",
                    tool_input={
                        **detail_input,
                        "page": 1,
                        "page_size": 5,
                    },
                    agent_step_log_id=step.id,
                    tool_func=lambda: product_tools.list_product_reviews(
                        tenant_id=state["tenant_id"],
                        product_no=product_no,
                        page=1,
                        page_size=5,
                    ),
                )

            if not detail_result.success:
                state["error_code"] = detail_result.error_code
                state["error_message"] = detail_result.error_message
            elif not sku_result.success:
                state["error_code"] = sku_result.error_code
                state["error_message"] = sku_result.error_message

            state["metadata"] = {
                **(state.get("metadata") or {}),
                "product_query_mode": "product_detail",
                "product_no": product_no,
                "with_reviews": wants_reviews,
            }

            await log_step_success(
                state,
                step_log_service=step_log_service,
                step=step,
                start=start,
                output_summary=summarize_value(
                    {
                        "mode": "product_detail",
                        "product_no": product_no,
                        "detail_success": detail_result.success,
                        "sku_success": sku_result.success,
                        "with_reviews": wants_reviews,
                    }
                ),
            )
            return state

        # 没有明确商品编号时，用用户输入做 keyword 搜索。
        keyword = message[:100] if message else None

        result = await call_tool_with_log(
            state,
            tool_call_log_service=tool_call_log_service,
            tool_name="list_products",
            tool_type="product",
            tool_input={
                "tenant_id": str(state["tenant_id"]),
                "keyword": keyword,
                "page": 1,
                "page_size": 5,
            },
            agent_step_log_id=step.id,
            tool_func=lambda: product_tools.list_products(
                tenant_id=state["tenant_id"],
                keyword=keyword,
                page=1,
                page_size=5,
            ),
        )

        if not result.success:
            state["error_code"] = result.error_code
            state["error_message"] = result.error_message

        state["metadata"] = {
            **(state.get("metadata") or {}),
            "product_query_mode": "keyword_search",
            "keyword": keyword,
        }

        await log_step_success(
            state,
            step_log_service=step_log_service,
            step=step,
            start=start,
            output_summary=summarize_value(
                {
                    "mode": "keyword_search",
                    "keyword": keyword,
                    "success": result.success,
                    "error_code": result.error_code,
                }
            ),
        )
        return state

    except Exception as exc:
        state["error_code"] = "PRODUCT_TOOL_NODE_FAILED"
        state["error_message"] = f"商品工具节点执行失败：{exc.__class__.__name__}"

        await log_step_failed(
            step_log_service=step_log_service,
            step=step,
            start=start,
            error_message=state["error_message"],
        )
        return state


async def aftersale_tool_node(
        state: CustomerServiceAgentState,
        *,
        aftersale_tools: AftersaleTools,
        step_log_service: AgentStepLogService,
        tool_call_log_service: ToolCallLogService,
) -> CustomerServiceAgentState:
    """售后工具节点。

    支持：
    - after_sale_ticket_no：查询售后单详情；
    - order_no / user_no：查询售后列表；
    - aftersale_apply：在信息齐全时创建基础售后单；
    - 信息不足：不强行创建，交给后续回答节点追问用户。
    """

    step, start = await log_step_start(
        state,
        step_log_service=step_log_service,
        step_name="aftersale_tool_node",
        step_order=30,
    )

    try:
        message = _safe_get_message(state)
        context = state.get("context") or {}
        entities = state.get("entities") or {}
        intent = state.get("intent")

        after_sale_ticket_no = (
                entities.get("after_sale_ticket_no")
                or context.get("after_sale_ticket_no")
                or context.get("ticket_no")
        )
        order_no = entities.get("order_no") or context.get("order_no")
        user_no = state.get("user_no") or context.get("user_no")

        # 1. 有售后单号：查询售后详情
        if after_sale_ticket_no:
            tool_input = {
                "tenant_id": str(state["tenant_id"]),
                "ticket_no": after_sale_ticket_no,
            }

            result = await call_tool_with_log(
                state,
                tool_call_log_service=tool_call_log_service,
                tool_name="get_aftersale_detail",
                tool_type="aftersale",
                tool_input=tool_input,
                agent_step_log_id=step.id,
                tool_func=lambda: aftersale_tools.get_aftersale_detail(
                    tenant_id=state["tenant_id"],
                    ticket_no=after_sale_ticket_no,
                ),
            )

            if not result.success:
                state["error_code"] = result.error_code
                state["error_message"] = result.error_message

            state["metadata"] = {
                **(state.get("metadata") or {}),
                "aftersale_mode": "detail",
                "after_sale_ticket_no": after_sale_ticket_no,
            }

            await log_step_success(
                state,
                step_log_service=step_log_service,
                step=step,
                start=start,
                output_summary=summarize_value(
                    {
                        "mode": "detail",
                        "ticket_no": after_sale_ticket_no,
                        "success": result.success,
                        "error_code": result.error_code,
                    }
                ),
            )
            return state

        # 2. 售后申请：只有信息齐全才创建，信息不足就追问
        if intent == CustomerServiceIntent.AFTERSALE_APPLY:
            required_fields = [
                "user_no",
                "order_no",
                "order_item_id",
                "after_sale_type",
                "reason",
            ]

            payload_data = {
                "tenant_id": state["tenant_id"],
                "user_no": user_no,
                "order_no": order_no,
                "order_item_id": context.get("order_item_id"),
                "after_sale_type": context.get("after_sale_type") or _guess_aftersale_type(message),
                "reason": context.get("reason") or message,
                "description": context.get("description") or message,
                "refund_amount": context.get("refund_amount"),
                "currency": context.get("currency") or "CNY",
                "evidence_json": context.get("evidence_json") or [],
                "metadata_json": {
                    **(context.get("metadata_json") or {}),
                    "created_by": "customer_service_agent",
                    "session_id": state.get("session_id"),
                    "agent_task_id": str(state.get("agent_task_id") or ""),
                },
            }

            missing_fields = [
                field
                for field in required_fields
                if payload_data.get(field) in {None, ""}
            ]

            if missing_fields:
                state["metadata"] = {
                    **(state.get("metadata") or {}),
                    "aftersale_mode": "need_more_info",
                    "missing_fields": missing_fields,
                }

                await log_step_success(
                    state,
                    step_log_service=step_log_service,
                    step=step,
                    start=start,
                    output_summary=summarize_value(
                        {
                            "mode": "need_more_info",
                            "missing_fields": missing_fields,
                        }
                    ),
                )
                return state

            payload = AfterSaleCreateRequest(**payload_data)

            result = await call_tool_with_log(
                state,
                tool_call_log_service=tool_call_log_service,
                tool_name="create_aftersale_ticket",
                tool_type="aftersale",
                tool_input={
                    **payload.model_dump(mode="json"),
                    "tenant_id": str(state["tenant_id"]),
                },
                agent_step_log_id=step.id,
                tool_func=lambda: aftersale_tools.create_aftersale_ticket(
                    payload=payload,
                ),
            )

            if not result.success:
                state["error_code"] = result.error_code
                state["error_message"] = result.error_message

            state["metadata"] = {
                **(state.get("metadata") or {}),
                "aftersale_mode": "create",
                "order_no": order_no,
                "success": result.success,
            }

            await log_step_success(
                state,
                step_log_service=step_log_service,
                step=step,
                start=start,
                output_summary=summarize_value(
                    {
                        "mode": "create",
                        "order_no": order_no,
                        "success": result.success,
                        "error_code": result.error_code,
                    }
                ),
            )
            return state

        # 3. 没有售后单号，但有 user_no / order_no：查询售后列表
        if user_no or order_no:
            tool_input = {
                "tenant_id": str(state["tenant_id"]),
                "user_no": user_no,
                "order_no": order_no,
                "page": 1,
                "page_size": 5,
            }

            result = await call_tool_with_log(
                state,
                tool_call_log_service=tool_call_log_service,
                tool_name="list_aftersales",
                tool_type="aftersale",
                tool_input=tool_input,
                agent_step_log_id=step.id,
                tool_func=lambda: aftersale_tools.list_aftersales(
                    tenant_id=state["tenant_id"],
                    user_no=user_no,
                    order_no=order_no,
                    page=1,
                    page_size=5,
                ),
            )

            if not result.success:
                state["error_code"] = result.error_code
                state["error_message"] = result.error_message

            state["metadata"] = {
                **(state.get("metadata") or {}),
                "aftersale_mode": "list",
                "user_no": user_no,
                "order_no": order_no,
            }

            await log_step_success(
                state,
                step_log_service=step_log_service,
                step=step,
                start=start,
                output_summary=summarize_value(
                    {
                        "mode": "list",
                        "user_no": user_no,
                        "order_no": order_no,
                        "success": result.success,
                        "error_code": result.error_code,
                    }
                ),
            )
            return state

        # 4. 什么关键信息都没有：不调用工具，后续追问
        state["metadata"] = {
            **(state.get("metadata") or {}),
            "aftersale_mode": "need_more_info",
            "missing_fields": ["user_no", "order_no 或 after_sale_ticket_no"],
        }

        await log_step_success(
            state,
            step_log_service=step_log_service,
            step=step,
            start=start,
            output_summary="售后查询缺少 user_no / order_no / after_sale_ticket_no，后续需要追问用户",
        )
        return state


    except Exception as exc:
        state["error_code"] = "AFTERSALE_TOOL_NODE_FAILED"
        state["error_message"] = f"售后工具节点执行失败：{exc.__class__.__name__}: {exc}"
        state["metadata"] = {
            **(state.get("metadata") or {}),
            "aftersale_mode": "failed",
            "aftersale_error_type": exc.__class__.__name__,
            "aftersale_error_message": str(exc),
        }

        await log_step_failed(
            step_log_service=step_log_service,
            step=step,
            start=start,
            error_message=state["error_message"],
        )

        return state


async def policy_rag_node(
        state: CustomerServiceAgentState,
        *,
        knowledge_tools: KnowledgeTools,
        step_log_service: AgentStepLogService,
        tool_call_log_service: ToolCallLogService,
) -> CustomerServiceAgentState:
    """政策 / 知识库 RAG 问答节点。

    用于：
    - 售后政策；
    - 七天无理由退货；
    - 退货 / 换货 / 退款规则；
    - 平台服务说明；
    - 商品说明类知识库问答。

    政策类问题必须尽量保留 citations，避免无来源回答。
    """

    step, start = await log_step_start(
        state,
        step_log_service=step_log_service,
        step_name="policy_rag_node",
        step_order=30,
    )

    try:
        question = _safe_get_message(state)

        tool_input = {
            "tenant_id": str(state["tenant_id"]),
            "question": question,
            "top_k": 5,
            "user_id": str(state.get("user_id")) if state.get("user_id") else None,
        }

        result = await call_tool_with_log(
            state,
            tool_call_log_service=tool_call_log_service,
            tool_name="rag_policy_ask",
            tool_type="knowledge",
            tool_input=tool_input,
            agent_step_log_id=step.id,
            tool_func=lambda: knowledge_tools.ask_policy(
                tenant_id=state["tenant_id"],
                question=question,
                top_k=5,
                request_id=state.get("request_id"),
                user_id=state.get("user_id"),
            ),
        )

        if result.success and isinstance(result.data, dict):
            state["rag_answer"] = result.data.get("answer")

            citations = (
                    result.data.get("citations")
                    or result.data.get("references")
                    or result.data.get("sources")
                    or result.data.get("chunks")
                    or result.data.get("documents")
                    or []
            )

            if isinstance(citations, list):
                state["citations"] = citations
            else:
                state["citations"] = []

            if isinstance(citations, list):
                state["citations"] = citations
            else:
                state["citations"] = []

            state["metadata"] = {
                **(state.get("metadata") or {}),
                "rag_prompt_template_id": result.data.get("prompt_template_id"),
                "rag_prompt_version_id": result.data.get("prompt_version_id"),
                "rag_citation_count": len(state.get("citations") or []),
            }
        else:
            state["error_code"] = result.error_code
            state["error_message"] = result.error_message
            state["citations"] = []

        await log_step_success(
            state,
            step_log_service=step_log_service,
            step=step,
            start=start,
            output_summary=summarize_value(
                {
                    "success": result.success,
                    "error_code": result.error_code,
                    "citation_count": len(state.get("citations") or []),
                }
            ),
        )
        return state

    except Exception as exc:
        state["error_code"] = "POLICY_RAG_NODE_FAILED"
        state["error_message"] = f"政策知识库节点执行失败：{exc.__class__.__name__}"

        await log_step_failed(
            step_log_service=step_log_service,
            step=step,
            start=start,
            error_message=state["error_message"],
        )
        return state


async def handoff_tool_node(
        state: CustomerServiceAgentState,
        *,
        ticket_tools: TicketTools,
        step_log_service: AgentStepLogService,
        tool_call_log_service: ToolCallLogService,
) -> CustomerServiceAgentState:
    """人工转接 / 投诉工单节点。

    用于：
    - 投诉；
    - 用户要求人工；
    - 赔付、退款争议等高风险；
    - 工具失败后的兜底转人工。
    """

    step, start = await log_step_start(
        state,
        step_log_service=step_log_service,
        step_name="handoff_tool_node",
        step_order=40,
    )

    try:
        message = _safe_get_message(state)
        context = state.get("context") or {}
        entities = state.get("entities") or {}

        should_transfer, reason = should_handoff(
            message=message,
            intent=state.get("intent"),
            confidence=state.get("confidence"),
            tool_results=state.get("tool_results") or [],
            citations=state.get("citations") or [],
        )

        handoff_reason = (
                reason
                or state.get("handoff_reason")
                or "当前问题需要人工客服进一步处理"
        )

        payload = CustomerServiceTicketCreateRequest(
            tenant_id=state["tenant_id"],
            user_no=state.get("user_no") or context.get("user_no"),
            order_no=context.get("order_no") or entities.get("order_no"),
            source="agent",
            channel="agent",
            category=(
                "complaint"
                if "投诉" in handoff_reason or "高风险" in handoff_reason
                else "manual_handoff"
            ),
            priority="high" if should_transfer else "normal",
            title="智能客服转人工",
            content=message,
            assigned_operator_id=None,
            metadata_json={
                "handoff_reason": handoff_reason,
                "intent": state.get("intent"),
                "confidence": state.get("confidence"),
                "session_id": state.get("session_id"),
                "agent_task_id": str(state.get("agent_task_id") or ""),
                "created_by": "customer_service_agent",
            },
        )

        result = await call_tool_with_log(
            state,
            tool_call_log_service=tool_call_log_service,
            tool_name="create_customer_service_ticket",
            tool_type="ticket",
            tool_input={
                **payload.model_dump(mode="json"),
                "tenant_id": str(state["tenant_id"]),
            },
            agent_step_log_id=step.id,
            tool_func=lambda: ticket_tools.create_customer_service_ticket(
                payload=payload,
            ),
        )

        state["handoff_required"] = True
        state["handoff_reason"] = handoff_reason

        if not result.success:
            state["error_code"] = result.error_code
            state["error_message"] = result.error_message
        else:
            state["metadata"] = {
                **(state.get("metadata") or {}),
                "handoff_ticket_created": True,
                "handoff_ticket": result.data,
            }

        await log_step_success(
            state,
            step_log_service=step_log_service,
            step=step,
            start=start,
            output_summary=summarize_value(
                {
                    "handoff_required": True,
                    "handoff_reason": handoff_reason,
                    "ticket_created": result.success,
                    "error_code": result.error_code,
                }
            ),
        )
        return state

    except Exception as exc:
        state["handoff_required"] = True
        state["handoff_reason"] = state.get("handoff_reason") or "人工转接节点执行异常"
        state["error_code"] = "HANDOFF_TOOL_NODE_FAILED"
        state["error_message"] = f"人工转接节点执行失败：{exc.__class__.__name__}"

        await log_step_failed(
            step_log_service=step_log_service,
            step=step,
            start=start,
            error_message=state["error_message"],
        )
        return state


async def validate_result_node(
        state: CustomerServiceAgentState,
        *,
        step_log_service: AgentStepLogService,
) -> CustomerServiceAgentState:
    """结果校验节点。

    统一判断：
    - 是否工具失败；
    - 是否低置信度；
    - 是否政策类问题无引用；
    - 是否需要转人工。
    """

    step, start = await log_step_start(
        state,
        step_log_service=step_log_service,
        step_name="validate_result_node",
        step_order=50,
    )

    try:
        should_transfer, reason = should_handoff(
            message=state.get("message"),
            intent=state.get("intent"),
            confidence=state.get("confidence"),
            tool_results=state.get("tool_results") or [],
            citations=state.get("citations") or [],
        )

        if should_transfer:
            state["handoff_required"] = True
            state["handoff_reason"] = reason or state.get("handoff_reason") or "需要人工客服处理"
        else:
            state["handoff_required"] = False
            state["handoff_reason"] = None

        state["metadata"] = {
            **(state.get("metadata") or {}),
            "validation": {
                "handoff_required": state.get("handoff_required"),
                "handoff_reason": state.get("handoff_reason"),
                "tool_result_count": len(state.get("tool_results") or []),
                "citation_count": len(state.get("citations") or []),
                "error_code": state.get("error_code"),
            },
        }

        await log_step_success(
            state,
            step_log_service=step_log_service,
            step=step,
            start=start,
            output_summary=summarize_value(state["metadata"].get("validation")),
        )
        return state

    except Exception as exc:
        state["error_code"] = "VALIDATE_RESULT_NODE_FAILED"
        state["error_message"] = f"结果校验节点执行失败：{exc.__class__.__name__}"

        await log_step_failed(
            step_log_service=step_log_service,
            step=step,
            start=start,
            error_message=state["error_message"],
        )
        return state


def _latest_tool_result(state: CustomerServiceAgentState) -> dict[str, Any] | None:
    tool_results = state.get("tool_results") or []
    if not tool_results:
        return None
    return tool_results[-1]


def _find_tool_result(
        state: CustomerServiceAgentState,
        tool_name: str,
) -> dict[str, Any] | None:
    """按工具名查找最近一次工具结果。"""

    tool_results = state.get("tool_results") or []

    for item in reversed(tool_results):
        if item.get("tool_name") == tool_name:
            return item

    return None


def _build_fallback_answer(state: CustomerServiceAgentState) -> str:
    """Prompt / 模型失败时的兜底回答。

    注意：
    - 不胡编政策；
    - 不假装售后已创建；
    - 有 RAG answer 优先用 RAG answer；
    - 需要人工时明确告知已转人工或将转人工。
    """

    if state.get("handoff_required"):
        reason = state.get("handoff_reason") or "当前问题需要人工客服进一步确认"
        return f"这个问题我已经为你转人工处理，客服会继续跟进。原因：{reason}。"

    if state.get("rag_answer"):
        return str(state["rag_answer"])

    metadata = state.get("metadata") or {}
    missing_fields = metadata.get("missing_fields")
    if missing_fields:
        return f"为了继续处理，请你补充这些信息：{', '.join(missing_fields)}。"

    latest_result = _latest_tool_result(state)
    if latest_result and not latest_result.get("success"):
        return (
            "我刚才查询时遇到问题，暂时无法完成处理。"
            "你可以稍后再试，或让我帮你转人工客服。"
        )

    intent = state.get("intent")

    if intent == CustomerServiceIntent.ORDER_QUERY:
        latest_result = _latest_tool_result(state)
        data = latest_result.get("data") if latest_result else None
        if isinstance(data, dict):
            order_no = data.get("order_no")
            order_status = data.get("order_status")
            payment_status = data.get("payment_status")
            fulfillment_status = data.get("fulfillment_status")
            logistics = data.get("logistics_snapshot_json") or {}
            tracking_no = logistics.get("tracking_no")
            carrier = logistics.get("carrier")

            status_map = {
                "completed": "已完成",
                "paid": "已支付",
                "delivered": "已送达",
                "unfulfilled": "待发货",
                "pending": "待处理",
                "canceled": "已取消",
            }

            return (
                    f"已查询到你的订单 {order_no or ''}："
                    f"订单状态为{status_map.get(order_status, order_status or '未知')}，"
                    f"支付状态为{status_map.get(payment_status, payment_status or '未知')}，"
                    f"履约状态为{status_map.get(fulfillment_status, fulfillment_status or '未知')}。"
                    + (
                        f"物流承运商为 {carrier}，单号 {tracking_no}。"
                        if carrier or tracking_no
                        else ""
                    )
            )
        return "我已经查询到你的订单信息，但还需要进一步核实具体物流状态。"

    if intent == CustomerServiceIntent.PRODUCT_QUERY:
        detail_result = _find_tool_result(state, "get_product_detail")
        sku_result = _find_tool_result(state, "list_product_skus")

        product_data = detail_result.get("data") if detail_result else None
        sku_data = sku_result.get("data") if sku_result else None

        product_title = None
        product_no = None

        if isinstance(product_data, dict):
            product_title = (
                    product_data.get("title")
                    or product_data.get("product_title")
                    or product_data.get("name")
            )
            product_no = product_data.get("product_no")

        sku_items: list[dict[str, Any]] = []

        if isinstance(sku_data, list):
            sku_items = [item for item in sku_data if isinstance(item, dict)]
        elif isinstance(sku_data, dict):
            items = sku_data.get("items") or sku_data.get("records") or sku_data.get("data")
            if isinstance(items, list):
                sku_items = [item for item in items if isinstance(item, dict)]

        if sku_items:
            sku_descriptions = []

            for sku in sku_items[:5]:
                sku_name = (
                        sku.get("sku_name")
                        or sku.get("name")
                        or sku.get("sku_no")
                        or "未命名规格"
                )
                price = (
                        sku.get("sale_price")
                        or sku.get("price")
                        or sku.get("unit_price")
                )
                stock = sku.get("stock") or sku.get("stock_quantity")

                parts = [str(sku_name)]
                if price is not None:
                    parts.append(f"价格 {price}")
                if stock is not None:
                    parts.append(f"库存 {stock}")

                sku_descriptions.append("，".join(parts))

            product_label = product_title or product_no or "该商品"

            return (
                    f"{product_label} 当前可选规格有："
                    + "；".join(sku_descriptions)
                    + "。"
            )

        if product_title or product_no:
            return f"已查询到商品 {product_title or product_no}，但暂时没有查到可展示的规格信息。"

        return "我已经查询了商品信息，但暂时没有拿到可展示的规格明细。"

    if intent in {
        CustomerServiceIntent.AFTERSALE_APPLY,
        CustomerServiceIntent.AFTERSALE_QUERY,
    }:
        return "我已经查询或处理了售后信息，请查看处理结果。"

    return "我已收到你的问题。为了更准确处理，请补充订单号、商品编号或更具体的问题描述。"


async def generate_answer_node(
        state: CustomerServiceAgentState,
        *,
        db: AsyncSession,
        prompt_service: Any,
        model_gateway: Any,
        step_log_service: AgentStepLogService,
) -> CustomerServiceAgentState:
    """最终回答生成节点。

    正常路径：
    - 使用 customer_service_answer Prompt；
    - 注入用户问题、意图、工具结果、RAG 引用、转人工信息；
    - 调用 ModelGateway.chat；
    - 写入 state.answer。

    兜底路径：
    - Prompt 缺失；
    - Prompt 变量缺失；
    - 模型失败；
    - 使用规则模板生成回答。
    """

    step, start = await log_step_start(
        state,
        step_log_service=step_log_service,
        step_name="generate_answer_node",
        step_order=60,
    )

    try:
        tool_results = state.get("tool_results") or []
        citations = state.get("citations") or []
        metadata = state.get("metadata") or {}

        variables = {
            # 兼容当前 cs_answer_default Prompt 的必填变量
            "user_question": state.get("message") or "",
            "user_profile": summarize_value(
                {
                    "user_id": str(state.get("user_id")) if state.get("user_id") else None,
                    "user_no": state.get("user_no"),
                    "session_id": state.get("session_id"),
                }
            ),
            "business_context": summarize_value(
                {
                    "intent": state.get("intent") or CustomerServiceIntent.UNKNOWN.value,
                    "confidence": state.get("confidence"),
                    "entities": state.get("entities") or {},
                    "tool_results": tool_results,
                    "handoff_required": bool(state.get("handoff_required")),
                    "handoff_reason": state.get("handoff_reason"),
                    "error_code": state.get("error_code"),
                    "error_message": state.get("error_message"),
                    "metadata": metadata,
                },
                max_length=2000,
            ),
            "policy_context": summarize_value(
                {
                    "rag_answer": state.get("rag_answer"),
                    "citations": citations,
                },
                max_length=2000,
            ),

            # 额外保留，兼容后续升级版 Prompt
            "user_message": state.get("message") or "",
            "conversation_summary": state.get("conversation_summary") or "",
            "intent": state.get("intent") or CustomerServiceIntent.UNKNOWN.value,
            "confidence": state.get("confidence"),
            "entities": state.get("entities") or {},
            "tool_results": tool_results,
            "rag_answer": state.get("rag_answer"),
            "citations": citations,
            "handoff_required": bool(state.get("handoff_required")),
            "handoff_reason": state.get("handoff_reason"),
            "error_code": state.get("error_code"),
            "error_message": state.get("error_message"),
            "metadata": metadata,
        }

        rendered_prompt = await prompt_service.render_prompt(
            db,
            payload=PromptRenderRequest(
                tenant_id=state["tenant_id"],
                scene="customer_service_answer",
                variables=variables,
            ),
        )

        model_config = rendered_prompt.model_config_json or {}
        provider = model_config.get("provider")
        model = model_config.get("model")

        model_response = await model_gateway.chat(
            ChatRequest(
                tenant_id=state["tenant_id"],
                request_id=state.get("request_id"),
                user_id=state.get("user_id"),
                provider=provider,
                model=model,
                prompt_template_id=rendered_prompt.template_id,
                prompt_version_id=rendered_prompt.version_id,
                messages=[
                    LLMMessage(
                        role="user",
                        content=rendered_prompt.rendered_content,
                    )
                ],
            )
        )

        answer = (model_response.content or "").strip()

        if (
                not answer
                or answer.startswith("[mock]")
                or "你是电商平台的智能客服助手" in answer
                or "请生成给用户的最终" in answer
        ):
            answer = _build_fallback_answer(state)
            answer_source = "fallback"
        else:
            answer_source = "llm"

        state["answer"] = answer
        state["metadata"] = {
            **(state.get("metadata") or {}),
            "answer_source": answer_source,
            "answer_prompt_template_id": str(rendered_prompt.template_id),
            "answer_prompt_version_id": str(rendered_prompt.version_id),
        }

        await log_step_success(
            state,
            step_log_service=step_log_service,
            step=step,
            start=start,
            output_summary=summarize_value(
                {
                    "answer_source": answer_source,
                    "answer": answer,
                }
            ),
        )
        return state

    except BaseAppException as exc:
        answer = _build_fallback_answer(state)
        state["answer"] = answer
        state["metadata"] = {
            **(state.get("metadata") or {}),
            "answer_source": "fallback",
            "fallback_cause": getattr(exc, "code", "BUSINESS_ERROR"),
        }

        await log_step_success(
            state,
            step_log_service=step_log_service,
            step=step,
            start=start,
            output_summary=summarize_value(
                {
                    "answer_source": "fallback",
                    "fallback_cause": getattr(exc, "code", "BUSINESS_ERROR"),
                    "answer": answer,
                }
            ),
        )
        return state

    except Exception as exc:
        answer = _build_fallback_answer(state)
        state["answer"] = answer
        state["metadata"] = {
            **(state.get("metadata") or {}),
            "answer_source": "fallback",
            "fallback_cause": exc.__class__.__name__,
        }

        await log_step_success(
            state,
            step_log_service=step_log_service,
            step=step,
            start=start,
            output_summary=summarize_value(
                {
                    "answer_source": "fallback",
                    "fallback_cause": exc.__class__.__name__,
                    "answer": answer,
                }
            ),
        )
        return state
