# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/05/04 08:56
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from langgraph.graph import END, StateGraph

from app.agents.operation_copilot.nodes import (
    build_metric_query_node,
    create_agent_task_node,
    execute_sql_node,
    finalize_task_node,
    generate_answer_node,
    guard_sql_node,
    parse_intent_node,
)
from app.agents.operation_copilot.state import OperationCopilotState


def build_operation_copilot_workflow():
    workflow = StateGraph(OperationCopilotState)

    workflow.add_node("create_task", create_agent_task_node)
    workflow.add_node("parse_intent", parse_intent_node)
    workflow.add_node("build_metric_query", build_metric_query_node)
    workflow.add_node("guard_sql", guard_sql_node)
    workflow.add_node("execute_sql", execute_sql_node)
    workflow.add_node("generate_answer", generate_answer_node)
    workflow.add_node("finalize_task", finalize_task_node)

    workflow.set_entry_point("create_task")

    workflow.add_edge("create_task", "parse_intent")
    workflow.add_edge("parse_intent", "build_metric_query")
    workflow.add_edge("build_metric_query", "guard_sql")
    workflow.add_edge("guard_sql", "execute_sql")
    workflow.add_edge("execute_sql", "generate_answer")
    workflow.add_edge("generate_answer", "finalize_task")
    workflow.add_edge("finalize_task", END)

    return workflow.compile()