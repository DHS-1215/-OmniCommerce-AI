# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/05/01 22:34
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from app.rag.retriever import RetrievalHit


class NoopReranker:
    """
    Reranker 占位实现。

    当前窗口 6A 不接真实 reranker。
    该类保持接口稳定，后续可替换为真实 reranker，例如：
    - bge-reranker
    - LLM-based reranker
    - 模型网关 rerank provider

    注意：
    当前实现只按已有 score 排序，不改变语义。
    """

    def rerank(
        self,
        *,
        query: str,
        hits: list[RetrievalHit],
        top_n: int,
    ) -> list[RetrievalHit]:
        if not hits:
            return []

        sorted_hits = sorted(
            hits,
            key=lambda item: item.score,
            reverse=True,
        )

        return sorted_hits[:top_n]