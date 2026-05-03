from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BaseAppException
from app.services.knowledge_service import KnowledgeService
from app.tools.base import (
    ToolResult,
    business_error_result,
    to_plain_data,
    unexpected_error_result,
)


class KnowledgeTools:
    """智能客服 Agent 可调用的知识库工具。"""

    def __init__(
        self,
        db: AsyncSession,
        knowledge_service: KnowledgeService,
    ) -> None:
        self.db = db
        self.knowledge_service = knowledge_service

    async def search_knowledge(
        self,
        *,
        tenant_id: UUID,
        query: str,
        top_k: int | None = None,
        request_id: str | None = None,
        user_id: UUID | None = None,
    ) -> ToolResult:
        tool_name = "search_knowledge"

        try:
            result = await self.knowledge_service.search(
                self.db,
                tenant_id=tenant_id,
                query=query,
                top_k=top_k,
                request_id=request_id,
                user_id=user_id,
            )
            return ToolResult.ok(
                tool_name=tool_name,
                data=to_plain_data(result),
            )
        except BaseAppException as exc:
            return business_error_result(tool_name, exc)
        except Exception as exc:
            return unexpected_error_result(tool_name, exc)

    async def ask_policy(
        self,
        *,
        tenant_id: UUID,
        question: str,
        top_k: int | None = None,
        request_id: str | None = None,
        user_id: UUID | None = None,
    ) -> ToolResult:
        tool_name = "rag_policy_ask"

        try:
            result = await self.knowledge_service.ask(
                self.db,
                tenant_id=tenant_id,
                question=question,
                top_k=top_k,
                request_id=request_id,
                user_id=user_id,
            )
            return ToolResult.ok(
                tool_name=tool_name,
                data=to_plain_data(result),
            )
        except BaseAppException as exc:
            return business_error_result(tool_name, exc)
        except Exception as exc:
            return unexpected_error_result(tool_name, exc)