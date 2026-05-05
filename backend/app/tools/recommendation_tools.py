# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/05/03 14:21
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from typing import Any
from uuid import UUID

from app.services.recommendation_service import RecommendationService
from app.tools.base import ToolResult, unexpected_error_result
from app.services.knowledge_service import KnowledgeService


class RecommendationTools:
    def __init__(
            self,
            db: Any,
            recommendation_service: RecommendationService | None = None,
            knowledge_service: KnowledgeService | None = None,
    ) -> None:
        self.db = db
        self.recommendation_service = recommendation_service or RecommendationService()
        self.knowledge_service = knowledge_service or KnowledgeService()

    async def parse_user_need(
            self,
            *,
            message: str,
            context: dict[str, Any] | None = None,
    ) -> ToolResult:
        tool_name = "parse_user_need"
        try:
            parsed_need = await self.recommendation_service.parse_user_need(
                message=message,
                context=context or {},
            )
            return ToolResult(
                success=True,
                tool_name=tool_name,
                data=parsed_need.model_dump(mode="json"),
            )
        except Exception as exc:
            return unexpected_error_result(tool_name=tool_name, exc=exc)

    async def recall_product_candidates(
            self,
            *,
            tenant_id: UUID,
            message: str,
            user_no: str | None = None,
            context: dict[str, Any] | None = None,
            limit: int = 5,
    ) -> ToolResult:
        tool_name = "recall_product_candidates"
        try:
            parsed_need = await self.recommendation_service.parse_user_need(
                message=message,
                context=context or {},
            )
            user_preferences = await self.recommendation_service.build_user_preference(
                self.db,
                tenant_id=tenant_id,
                user_no=user_no,
                parsed_need=parsed_need,
            )
            recommendations, comparisons = (
                await self.recommendation_service.build_structured_recommendations(
                    self.db,
                    tenant_id=tenant_id,
                    parsed_need=parsed_need,
                    user_preferences=user_preferences,
                    limit=limit,
                )
            )

            return ToolResult(
                success=True,
                tool_name=tool_name,
                data={
                    "parsed_need": parsed_need.model_dump(mode="json"),
                    "user_preferences": user_preferences,
                    "recommendations": [
                        item.model_dump(mode="json") for item in recommendations
                    ],
                    "comparisons": [
                        item.model_dump(mode="json") for item in comparisons
                    ],
                },
            )
        except Exception as exc:
            return unexpected_error_result(tool_name=tool_name, exc=exc)

    async def compare_product_skus(
            self,
            *,
            tenant_id: UUID,
            message: str,
            context: dict[str, Any] | None = None,
    ) -> ToolResult:
        tool_name = "compare_product_skus"
        try:
            parsed_need = await self.recommendation_service.parse_user_need(
                message=message,
                context=context or {},
            )
            recommendations, comparisons = (
                await self.recommendation_service.build_structured_recommendations(
                    self.db,
                    tenant_id=tenant_id,
                    parsed_need=parsed_need,
                    user_preferences=parsed_need.preferences,
                    limit=5,
                )
            )
            return ToolResult(
                success=True,
                tool_name=tool_name,
                data={
                    "parsed_need": parsed_need.model_dump(mode="json"),
                    "recommendations": [
                        item.model_dump(mode="json") for item in recommendations
                    ],
                    "comparisons": [
                        item.model_dump(mode="json") for item in comparisons
                    ],
                },
            )
        except Exception as exc:
            return unexpected_error_result(tool_name=tool_name, exc=exc)

    async def ask_shopping_knowledge(
            self,
            *,
            tenant_id: UUID,
            question: str,
            request_id: str | None = None,
            top_k: int = 3,
    ) -> ToolResult:
        """调用 KnowledgeService 获取选购知识。

        注意：
        - 只能通过 KnowledgeService。
        - 不直接查 Qdrant / OpenSearch。
        - 返回内容只能增强推荐解释，不能新增商品或 SKU。
        """

        tool_name = "ask_shopping_knowledge"

        try:
            result = await self.knowledge_service.ask(
                self.db,
                tenant_id=tenant_id,
                question=question,
                top_k=top_k,
                request_id=request_id,
                user_id=None,
            )

            return ToolResult(
                success=True,
                tool_name=tool_name,
                data={
                    "question": result.question,
                    "answer": result.answer,
                    "citations": [
                        citation.model_dump(mode="json")
                        for citation in result.citations
                    ],
                    "prompt_template_id": str(result.prompt_template_id) if result.prompt_template_id else None,
                    "prompt_version_id": str(result.prompt_version_id) if result.prompt_version_id else None,
                },
            )

        except Exception as exc:
            return unexpected_error_result(tool_name=tool_name, exc=exc)
