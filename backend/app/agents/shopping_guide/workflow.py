# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/05/03 14:39
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from langgraph.graph import END, StateGraph

from app.agents.shopping_guide.nodes import (
    compare_skus_node,
    create_agent_task_node,
    finalize_task_node,
    generate_recommendation_node,
    parse_need_node,
    recall_candidates_node,
    summarize_reviews_node,
    enrich_shopping_knowledge_node,
)
from app.agents.shopping_guide.state import ShoppingGuideState


def build_shopping_guide_workflow():
    workflow = StateGraph(ShoppingGuideState)

    workflow.add_node("create_task", create_agent_task_node)
    workflow.add_node("parse_need", parse_need_node)
    workflow.add_node("recall_candidates", recall_candidates_node)
    workflow.add_node("compare_skus", compare_skus_node)
    workflow.add_node("summarize_reviews", summarize_reviews_node)
    workflow.add_node("generate_recommendation", generate_recommendation_node)
    workflow.add_node("finalize_task", finalize_task_node)

    workflow.set_entry_point("create_task")

    workflow.add_edge("create_task", "parse_need")
    workflow.add_edge("parse_need", "recall_candidates")
    workflow.add_edge("recall_candidates", "compare_skus")
    workflow.add_edge("compare_skus", "summarize_reviews")
    workflow.add_edge("summarize_reviews", "enrich_shopping_knowledge")
    workflow.add_edge("enrich_shopping_knowledge", "generate_recommendation")
    workflow.add_edge("generate_recommendation", "finalize_task")
    workflow.add_edge("finalize_task", END)

    workflow.add_node("enrich_shopping_knowledge", enrich_shopping_knowledge_node)

    return workflow.compile()
