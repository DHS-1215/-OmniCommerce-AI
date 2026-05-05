# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/05/04 08:58
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
import time
from typing import Any

from app.agents.operation_copilot.intents import detect_operation_intent, extract_metric_keys
from app.agents.operation_copilot.state import OperationCopilotState
from app.llm.schemas import ChatRequest, LLMMessage
from app.schemas.prompt import PromptRenderRequest
from app.tools.base import tool_result_to_log_summary


async def create_agent_task_node(state: OperationCopilotState) -> OperationCopilotState:
    started_at = time.perf_counter()

    metadata = dict(state.get("metadata") or {})
    metadata["agent_type"] = "operation_copilot"

    agent_task_service = state["runtime"].get("agent_task_service")

    agent_task_id = None
    agent_task_no = None

    if agent_task_service is not None:
        try:
            task = await agent_task_service.create_task(
                tenant_id=state["tenant_id"],
                agent_type="operation_copilot",
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


async def parse_intent_node(state: OperationCopilotState) -> OperationCopilotState:
    started_at = time.perf_counter()

    context = state.get("context") or {}

    intent = detect_operation_intent(state["message"], context)
    metric_keys = extract_metric_keys(state["message"], context)

    state["intent"] = intent
    state["metric_keys"] = metric_keys

    await _log_step(
        state,
        step_name="parse_intent",
        step_order=2,
        input_summary=state["message"],
        output_summary=f"intent={intent}, metric_keys={metric_keys}",
        status="success",
        latency_ms=_latency_ms(started_at),
    )

    return state


async def build_metric_query_node(state: OperationCopilotState) -> OperationCopilotState:
    started_at = time.perf_counter()
    tools = state["runtime"]["bi_tools"]

    metric_keys = state.get("metric_keys") or []
    plans: list[dict[str, Any]] = []
    metrics: list[dict[str, Any]] = []

    for metric_key in metric_keys:
        result = await tools.build_metric_query(
            metric_key=metric_key,
            tenant_id=state["tenant_id"],
            context=state.get("context") or {},
        )

        state.setdefault("tool_calls", []).append(_tool_call_view(result))

        await _log_tool_call(
            state,
            tool_name=result.tool_name,
            input_summary=f"metric_key={metric_key}",
            output_summary=tool_result_to_log_summary(result),
            status="success" if result.success else "failed",
            latency_ms=_latency_ms(started_at),
            error_code=result.error_code,
            error_message=result.error_message,
        )

        data = result.data or {}
        if result.success:
            plans.append(data)
            metrics.append(
                {
                    "metric_key": data.get("metric_key"),
                    "metric_name": data.get("metric_name"),
                    "status": data.get("status"),
                    "source_tables": data.get("source_tables") or [],
                }
            )
        else:
            metrics.append(
                {
                    "metric_key": metric_key,
                    "status": result.error_code,
                    "message": result.error_message,
                    "data": data,
                }
            )

    first_plan = next((plan for plan in plans if plan.get("sql")), None)

    state["metric_plans"] = plans
    state["metrics"] = metrics
    state["sql"] = first_plan.get("sql") if first_plan else None
    state.setdefault("metadata", {})["metric_plan_count"] = len(plans)

    await _log_step(
        state,
        step_name="build_metric_query",
        step_order=3,
        input_summary=str(metric_keys),
        output_summary=f"plans={len(plans)}, executable_sql={bool(state.get('sql'))}",
        status="success",
        latency_ms=_latency_ms(started_at),
    )

    return state


async def guard_sql_node(state: OperationCopilotState) -> OperationCopilotState:
    started_at = time.perf_counter()
    tools = state["runtime"]["bi_tools"]

    sql = state.get("sql")
    if not sql:
        state["sql_guard"] = {
            "passed": False,
            "error_code": "SQL_NOT_GENERATED",
            "rejected_reason": "当前请求没有生成可执行 SQL，可能是指标数据源缺失。",
        }

        await _log_step(
            state,
            step_name="guard_sql",
            step_order=4,
            input_summary="sql=None",
            output_summary="SQL_NOT_GENERATED",
            status="success",
            latency_ms=_latency_ms(started_at),
        )
        return state

    result = await tools.guard_sql(sql=sql)
    state.setdefault("tool_calls", []).append(_tool_call_view(result))

    await _log_tool_call(
        state,
        tool_name=result.tool_name,
        input_summary=sql[:500],
        output_summary=tool_result_to_log_summary(result),
        status="success" if result.success else "failed",
        latency_ms=_latency_ms(started_at),
        error_code=result.error_code,
        error_message=result.error_message,
    )

    state["sql_guard"] = result.data if result.success else (result.data or {
        "passed": False,
        "error_code": result.error_code,
        "rejected_reason": result.error_message,
    })

    if not result.success:
        state["error_code"] = result.error_code
        state["error_message"] = result.error_message

    await _log_step(
        state,
        step_name="guard_sql",
        step_order=4,
        input_summary=sql[:500],
        output_summary=str(state.get("sql_guard"))[:500],
        status="success" if result.success else "failed",
        latency_ms=_latency_ms(started_at),
    )

    return state


async def execute_sql_node(state: OperationCopilotState) -> OperationCopilotState:
    started_at = time.perf_counter()
    tools = state["runtime"]["bi_tools"]

    sql = state.get("sql")
    sql_guard = state.get("sql_guard") or {}

    if not sql or not sql_guard.get("passed"):
        await _log_step(
            state,
            step_name="execute_sql",
            step_order=5,
            input_summary=str(sql_guard)[:500],
            output_summary="skipped",
            status="success",
            latency_ms=_latency_ms(started_at),
        )
        return state

    params: dict[str, Any] = {}
    for plan in state.get("metric_plans") or []:
        if plan.get("sql") == sql:
            params = plan.get("params") or {}
            break

    result = await tools.execute_readonly_sql(
        sql=sql,
        params=params,
        max_rows=100,
    )

    state.setdefault("tool_calls", []).append(_tool_call_view(result))

    await _log_tool_call(
        state,
        tool_name=result.tool_name,
        input_summary=sql[:500],
        output_summary=tool_result_to_log_summary(result),
        status="success" if result.success else "failed",
        latency_ms=_latency_ms(started_at),
        error_code=result.error_code,
        error_message=result.error_message,
    )

    if result.success:
        data = result.data or {}
        state["query_result"] = data.get("query_result")
    else:
        state["error_code"] = result.error_code
        state["error_message"] = result.error_message

    await _log_step(
        state,
        step_name="execute_sql",
        step_order=5,
        input_summary=sql[:500],
        output_summary=str(state.get("query_result") or result.error_message)[:500],
        status="success" if result.success else "failed",
        latency_ms=_latency_ms(started_at),
    )

    return state


async def generate_answer_node(state: OperationCopilotState) -> OperationCopilotState:
    started_at = time.perf_counter()

    query_result = state.get("query_result")
    metrics = state.get("metrics") or []

    fallback_answer = _build_fallback_answer(state)

    answer = fallback_answer
    report = None
    prompt_template_id = None
    prompt_version_id = None
    llm_used = False

    prompt_service = state["runtime"].get("prompt_service")
    model_gateway = state["runtime"].get("model_gateway")
    db = state["runtime"].get("db")

    # 只有明确进入运营报告流程时才调用 LLM 生成报告。
    # 普通指标查询只做规则解释，避免无意义触发 operation_report_generation Prompt。
    # 报告生成必须基于真实 query_result，不允许模型自由编数据。
    if (
        state.get("intent") == "operation_report"
        and prompt_service is not None
        and model_gateway is not None
        and db is not None
        and query_result
    ):
        try:
            rendered = await prompt_service.render_prompt(
                db,
                payload=PromptRenderRequest(
                    tenant_id=state["tenant_id"],
                    scene="operation_report_generation",
                    variables={
                        "user_question": state["message"],
                        "metrics": str(metrics)[:4000],
                        "query_result": str(query_result)[:4000],
                        "sql": str(state.get("sql") or "")[:4000],
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
                    temperature=model_config.get("temperature", 0.2),
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
            if llm_content and not llm_content.startswith("[mock]"):
                answer = llm_content
                report = llm_content
                llm_used = True

        except Exception as exc:
            metadata = dict(state.get("metadata") or {})
            metadata["operation_report_generation_error"] = str(exc)
            state["metadata"] = metadata

    metadata = dict(state.get("metadata") or {})
    metadata["prompt_template_id"] = str(prompt_template_id) if prompt_template_id else None
    metadata["prompt_version_id"] = str(prompt_version_id) if prompt_version_id else None
    metadata["answer_source"] = "llm_report" if llm_used else "rule_fallback"
    metadata[
        "report_generation_boundary"] = "Report can only use real query_result; model is not allowed to invent data."

    state["answer"] = answer
    state["report"] = report
    state["metadata"] = metadata

    await _log_step(
        state,
        step_name="generate_answer",
        step_order=6,
        input_summary=state["message"],
        output_summary=answer[:500],
        status="success",
        latency_ms=_latency_ms(started_at),
    )

    return state


async def finalize_task_node(state: OperationCopilotState) -> OperationCopilotState:
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
                    error_message=state.get("error_message") or state.get("error_code") or "operation copilot failed",
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


def _build_fallback_answer(state: OperationCopilotState) -> str:
    metrics = state.get("metrics") or []
    query_result = state.get("query_result")
    sql_guard = state.get("sql_guard") or {}

    unavailable = [
        item for item in metrics
        if item.get("status") and item.get("status") != "available"
    ]

    if unavailable and not query_result:
        lines = ["当前有指标无法直接计算："]
        for item in unavailable:
            metric_key = item.get("metric_key")
            message = item.get("message") or (item.get("data") or {}).get("unavailable_reason")
            lines.append(f"- {metric_key}: {message}")
        return "\n".join(lines)

    if not sql_guard.get("passed") and not query_result:
        return f"SQL 未执行：{sql_guard.get('rejected_reason') or sql_guard.get('error_code') or '未通过安全检查'}"

    if query_result:
        rows = query_result.get("rows") or []
        if rows:
            first_row = rows[0]
            metric_text = "，".join([f"{key}={value}" for key, value in first_row.items()])
            return (
                f"已完成运营指标查询。核心结果：{metric_text}。"
                "数据来自只读 SQL 查询，并且已通过 SQL Guard 安全检查。"
            )
        return "查询已执行，但当前条件下没有返回数据。"

    return "当前没有可展示的查询结果。"


async def _log_step(
        state: OperationCopilotState,
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
        state: OperationCopilotState,
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
            tool_type="bi",
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


def _tool_call_view(result: Any) -> dict[str, Any]:
    return {
        "tool_name": result.tool_name,
        "success": result.success,
        "error_code": result.error_code,
        "error_message": result.error_message,
    }


def _latency_ms(started_at: float) -> int:
    return int((time.perf_counter() - started_at) * 1000)
