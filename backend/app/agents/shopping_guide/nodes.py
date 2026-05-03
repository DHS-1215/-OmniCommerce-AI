# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/05/03 14:35
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
import inspect
import time
from typing import Any
from uuid import UUID

from app.agents.shopping_guide.intents import detect_shopping_intent
from app.agents.shopping_guide.state import ShoppingGuideState
from app.tools.base import tool_result_to_log_summary

from app.schemas.prompt import PromptRenderRequest
from app.llm.schemas import ChatRequest, LLMMessage


async def create_agent_task_node(state: ShoppingGuideState) -> ShoppingGuideState:
    started_at = time.perf_counter()

    metadata = dict(state.get("metadata") or {})
    metadata["agent_type"] = "shopping_guide"

    agent_task_service = state["runtime"].get("agent_task_service")

    agent_task_id = None
    agent_task_no = None

    if agent_task_service is not None:
        try:
            task = await agent_task_service.create_task(
                tenant_id=state["tenant_id"],
                agent_type="shopping_guide",
                session_id=state["session_id"],
                input_summary=state["message"][:500],
                request_id=state.get("request_id"),
                user_id=None,
                intent=None,
            )

            agent_task_id = task.id
            agent_task_no = task.task_no
            state["runtime"]["agent_task"] = task

        except Exception as exc:
            metadata["agent_task_log_error"] = str(exc)

    state["agent_task_id"] = agent_task_id
    state["agent_task_no"] = agent_task_no
    state["metadata"] = metadata

    await _log_step(
        state,
        step_name="create_agent_task",
        step_order=1,
        input_summary=state["message"],
        output_summary=f"agent_task_id={agent_task_id}",
        status="success",
        latency_ms=_latency_ms(started_at),
    )

    return state


async def parse_need_node(state: ShoppingGuideState) -> ShoppingGuideState:
    started_at = time.perf_counter()
    tools = state["runtime"]["recommendation_tools"]

    intent = detect_shopping_intent(
        state["message"],
        state.get("context") or {},
    )

    result = await tools.parse_user_need(
        message=state["message"],
        context=state.get("context") or {},
    )

    tool_call = _tool_call_view(result)
    state.setdefault("tool_calls", []).append(tool_call)

    await _log_tool_call(
        state,
        tool_name=result.tool_name,
        input_summary=state["message"],
        output_summary=tool_result_to_log_summary(result),
        status="success" if result.success else "failed",
        latency_ms=_latency_ms(started_at),
        error_code=result.error_code,
        error_message=result.error_message,
    )

    if result.success:
        parsed_need = result.data or {}
        state["parsed_need"] = parsed_need
        state["budget"] = parsed_need.get("budget")
        state["scenario"] = parsed_need.get("scenario")
        state["preferences"] = parsed_need.get("preferences") or []
    else:
        state["error_code"] = result.error_code
        state["error_message"] = result.error_message

    state["intent"] = intent

    await _log_step(
        state,
        step_name="parse_need",
        step_order=2,
        input_summary=state["message"],
        output_summary=str(state.get("parsed_need") or {})[:500],
        status="success" if result.success else "failed",
        latency_ms=_latency_ms(started_at),
    )

    return state


async def recall_candidates_node(state: ShoppingGuideState) -> ShoppingGuideState:
    started_at = time.perf_counter()
    tools = state["runtime"]["recommendation_tools"]

    result = await tools.recall_product_candidates(
        tenant_id=state["tenant_id"],
        message=state["message"],
        user_no=state.get("user_no"),
        context=state.get("context") or {},
        limit=5,
    )

    state.setdefault("tool_calls", []).append(_tool_call_view(result))

    await _log_tool_call(
        state,
        tool_name=result.tool_name,
        input_summary=state["message"],
        output_summary=tool_result_to_log_summary(result),
        status="success" if result.success else "failed",
        latency_ms=_latency_ms(started_at),
        error_code=result.error_code,
        error_message=result.error_message,
    )

    if result.success:
        data = result.data or {}
        state["parsed_need"] = data.get("parsed_need") or state.get("parsed_need") or {}
        state["recommendations"] = data.get("recommendations") or []
        state["comparisons"] = data.get("comparisons") or []
        state["preferences"] = data.get("user_preferences") or state.get("preferences") or []
    else:
        state["error_code"] = result.error_code
        state["error_message"] = result.error_message

    await _log_step(
        state,
        step_name="recall_candidates",
        step_order=3,
        input_summary=state["message"],
        output_summary=f"recommendations={len(state.get('recommendations') or [])}",
        status="success" if result.success else "failed",
        latency_ms=_latency_ms(started_at),
    )

    return state


async def compare_skus_node(state: ShoppingGuideState) -> ShoppingGuideState:
    started_at = time.perf_counter()

    # 第二批先复用 recall_candidates_node 产生的 comparisons。
    # 如果用户明确要求对比 SKU，而 comparisons 为空，再调用 compare_product_skus。
    comparisons = state.get("comparisons") or []

    if not comparisons and state.get("intent") == "sku_compare":
        tools = state["runtime"]["recommendation_tools"]
        result = await tools.compare_product_skus(
            tenant_id=state["tenant_id"],
            message=state["message"],
            context=state.get("context") or {},
        )
        state.setdefault("tool_calls", []).append(_tool_call_view(result))

        await _log_tool_call(
            state,
            tool_name=result.tool_name,
            input_summary=state["message"],
            output_summary=tool_result_to_log_summary(result),
            status="success" if result.success else "failed",
            latency_ms=_latency_ms(started_at),
            error_code=result.error_code,
            error_message=result.error_message,
        )

        if result.success:
            data = result.data or {}
            state["comparisons"] = data.get("comparisons") or []
            if not state.get("recommendations"):
                state["recommendations"] = data.get("recommendations") or []

    await _log_step(
        state,
        step_name="compare_skus",
        step_order=4,
        input_summary=state["message"],
        output_summary=f"comparisons={len(state.get('comparisons') or [])}",
        status="success",
        latency_ms=_latency_ms(started_at),
    )

    return state


async def summarize_reviews_node(state: ShoppingGuideState) -> ShoppingGuideState:
    started_at = time.perf_counter()

    # Review summary 已经由 RecommendationService 结构化生成。
    review_summary_count = 0
    for item in state.get("recommendations") or []:
        if item.get("review_summary"):
            review_summary_count += 1

    await _log_step(
        state,
        step_name="summarize_reviews",
        step_order=5,
        input_summary=state["message"],
        output_summary=f"review_summary_count={review_summary_count}",
        status="success",
        latency_ms=_latency_ms(started_at),
    )

    return state


async def generate_recommendation_node(state: ShoppingGuideState) -> ShoppingGuideState:
    started_at = time.perf_counter()

    recommendation_service = state["runtime"]["recommendation_service"]
    prompt_service = state["runtime"].get("prompt_service")
    model_gateway = state["runtime"].get("model_gateway")
    db = state["runtime"].get("db")

    recommendations = state.get("recommendations") or []
    parsed_need = state.get("parsed_need") or {}

    fallback_answer = recommendation_service.build_fallback_answer(
        parsed_need=_parsed_need_from_dict(recommendation_service, parsed_need, state),
        recommendations=[
            _recommendation_from_dict(item)
            for item in recommendations
        ],
    )

    answer = fallback_answer
    prompt_template_id = None
    prompt_version_id = None
    llm_used = False

    # LLM 只允许润色话术，不允许修改 recommendations / product_no / sku_no / price / stock。
    if prompt_service is not None and model_gateway is not None:
        try:
            rendered = await prompt_service.render_prompt(
                db,
                payload=PromptRenderRequest(
                    tenant_id=state["tenant_id"],
                    scene="shopping_guide_recommendation",
                    variables={
                        "user_need": state["message"],
                        "budget": str(state.get("budget") or ""),
                        "user_preference": ", ".join(state.get("preferences") or []),
                        "candidate_products": str(recommendations)[:4000],
                    },
                ),
            )

            prompt_template_id = rendered.template_id
            prompt_version_id = rendered.version_id

            model_config = rendered.model_config_json or {}

            chat_response = await model_gateway.chat(
                ChatRequest(
                    tenant_id=state["tenant_id"],
                    request_id=state.get("request_id"),
                    prompt_template_id=prompt_template_id,
                    prompt_version_id=prompt_version_id,
                    provider=model_config.get("provider"),
                    model=model_config.get("model"),
                    temperature=model_config.get("temperature", 0.7),
                    max_tokens=model_config.get("max_tokens"),
                    messages=[
                        LLMMessage(
                            role="user",
                            content=rendered.rendered_content,
                        )
                    ],
                )
            )

            llm_content = chat_response.content

            # mock provider 常会复读 Prompt。出现这种情况时使用规则 fallback。
            if llm_content and not llm_content.startswith("[mock]"):
                answer = llm_content
                llm_used = True

        except Exception as exc:
            metadata = dict(state.get("metadata") or {})
            metadata["llm_polish_error"] = str(exc)
            state["metadata"] = metadata

    metadata = dict(state.get("metadata") or {})
    metadata["prompt_template_id"] = str(prompt_template_id) if prompt_template_id else None
    metadata["prompt_version_id"] = str(prompt_version_id) if prompt_version_id else None
    metadata["answer_source"] = "llm_polish" if llm_used else "rule_fallback"
    metadata["llm_boundary"] = (
        "LLM only polishes shopping guide answer; "
        "structured recommendations are generated by ProductService + RecommendationService rules."
    )

    state["answer"] = answer
    state["metadata"] = metadata

    await _log_step(
        state,
        step_name="generate_recommendation",
        step_order=6,
        input_summary=state["message"],
        output_summary=answer[:500],
        status="success",
        latency_ms=_latency_ms(started_at),
    )

    return state


async def finalize_task_node(state: ShoppingGuideState) -> ShoppingGuideState:
    started_at = time.perf_counter()

    agent_task_service = state["runtime"].get("agent_task_service")
    task = state["runtime"].get("agent_task")

    status = "success"
    if state.get("error_code"):
        status = "failed"

    if agent_task_service is not None and task is not None:
        try:
            if status == "failed":
                await agent_task_service.mark_failed(
                    task=task,
                    error_message=state.get("error_message") or state.get("error_code") or "shopping guide failed",
                    intent=state.get("intent"),
                )
            else:
                await agent_task_service.mark_success(
                    task=task,
                    output_summary=(state.get("answer") or "")[:500],
                    intent=state.get("intent"),
                    handoff_required=False,
                    handoff_reason=None,
                )
        except Exception as exc:
            metadata = dict(state.get("metadata") or {})
            metadata["finalize_task_log_error"] = str(exc)
            state["metadata"] = metadata

    await _log_step(
        state,
        step_name="finalize_task",
        step_order=7,
        input_summary=state["message"],
        output_summary=status,
        status="success",
        latency_ms=_latency_ms(started_at),
    )

    return state


async def _log_step(
        state: ShoppingGuideState,
        *,
        step_name: str,
        step_order: int,
        input_summary: str,
        output_summary: str,
        status: str,
        latency_ms: int,
) -> None:
    step_log_service = state["runtime"].get("step_log_service")

    if step_log_service is None or not state.get("agent_task_id"):
        return

    try:
        step = await step_log_service.create_step(
            tenant_id=state["tenant_id"],
            agent_task_id=state["agent_task_id"],
            step_name=step_name,
            step_order=step_order,
            input_summary=input_summary[:500],
            request_id=state.get("request_id"),
            status="running",
        )

        if status == "failed":
            await step_log_service.mark_failed(
                step=step,
                error_message=output_summary[:500],
                latency_ms=latency_ms,
            )
        else:
            await step_log_service.mark_success(
                step=step,
                output_summary=output_summary[:500],
                latency_ms=latency_ms,
            )

    except Exception as exc:
        metadata = dict(state.get("metadata") or {})
        metadata.setdefault("step_log_errors", []).append(
            {
                "step_name": step_name,
                "error": str(exc),
            }
        )
        state["metadata"] = metadata


async def _log_tool_call(
        state: ShoppingGuideState,
        *,
        tool_name: str,
        input_summary: str,
        output_summary: str,
        status: str,
        latency_ms: int,
        error_code: str | None = None,
        error_message: str | None = None,
) -> None:
    tool_call_log_service = state["runtime"].get("tool_call_log_service")

    if tool_call_log_service is None or not state.get("agent_task_id"):
        return

    try:
        await tool_call_log_service.create_tool_call_log(
            tenant_id=state["tenant_id"],
            agent_task_id=state["agent_task_id"],
            tool_name=tool_name,
            tool_type="recommendation",
            input_summary=input_summary[:500],
            output_summary=output_summary[:500],
            status=status,
            latency_ms=latency_ms,
            request_id=state.get("request_id"),
            agent_step_log_id=None,
            error_code=error_code,
            error_message=error_message,
        )
    except Exception as exc:
        metadata = dict(state.get("metadata") or {})
        metadata.setdefault("tool_call_log_errors", []).append(
            {
                "tool_name": tool_name,
                "error": str(exc),
            }
        )
        state["metadata"] = metadata


async def _call_first_existing(obj: Any, *, method_names: list[str], **kwargs: Any) -> Any:
    last_error: Exception | None = None

    for method_name in method_names:
        method = getattr(obj, method_name, None)
        if method is None:
            continue

        try:
            filtered_kwargs = _filter_kwargs(method, kwargs)
            result = method(**filtered_kwargs)
            if inspect.isawaitable(result):
                return await result
            return result
        except TypeError as exc:
            last_error = exc
            continue

    if last_error:
        raise last_error

    raise AttributeError(f"No supported method found on {obj}: {method_names}")


def _filter_kwargs(method: Any, kwargs: dict[str, Any]) -> dict[str, Any]:
    signature = inspect.signature(method)
    parameters = signature.parameters

    if any(param.kind == inspect.Parameter.VAR_KEYWORD for param in parameters.values()):
        return kwargs

    return {key: value for key, value in kwargs.items() if key in parameters}


def _latency_ms(started_at: float) -> int:
    return int((time.perf_counter() - started_at) * 1000)


def _get_value(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _tool_call_view(result: Any) -> dict[str, Any]:
    return {
        "tool_name": result.tool_name,
        "success": result.success,
        "error_code": result.error_code,
        "error_message": result.error_message,
    }


def _parsed_need_from_dict(recommendation_service: Any, parsed_need: dict[str, Any], state: ShoppingGuideState) -> Any:
    # 避免在 nodes.py 里重复 import 全量 schema。
    # 使用 RecommendationService 自身重新解析一次，fallback 只用于生成文本。
    # 这里走同步兜底对象会太绕，所以直接构造最小对象。
    from app.schemas.shopping_guide import ShoppingGuideBudget, ShoppingGuideNeed

    budget = parsed_need.get("budget")
    budget_obj = None
    if isinstance(budget, dict):
        budget_obj = ShoppingGuideBudget(**budget)

    return ShoppingGuideNeed(
        user_need=parsed_need.get("user_need") or state["message"],
        budget=budget_obj,
        scenario=parsed_need.get("scenario"),
        preferences=parsed_need.get("preferences") or [],
        product_no=parsed_need.get("product_no"),
        sku_no=parsed_need.get("sku_no"),
        keywords=parsed_need.get("keywords") or [],
    )


def _recommendation_from_dict(item: dict[str, Any]) -> Any:
    from app.schemas.shopping_guide import ShoppingGuideRecommendationItem

    return ShoppingGuideRecommendationItem(**item)
