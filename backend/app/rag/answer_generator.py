from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.gateway import ModelGateway
from app.llm.schemas import ChatRequest, LLMMessage
from app.schemas.prompt import PromptRenderRequest
from app.services.prompt_service import PromptService


@dataclass(slots=True)
class RagAnswerResult:
    """
    RAG 回答生成结果。
    """

    answer: str
    prompt_template_id: UUID | None = None
    prompt_version_id: UUID | None = None
    model_provider: str | None = None
    model_name: str | None = None


class RagAnswerGenerator:
    """
    RAG 回答生成器。

    职责：
    - 通过 PromptService 渲染 rag_answer_generation Prompt
    - 通过 ModelGateway.chat() 生成回答
    - 将 prompt_template_id / prompt_version_id 传给模型网关用于日志追踪

    禁止：
    - 直接硬编码完整 Prompt
    - 直接调用外部模型 API
    """

    RAG_PROMPT_SCENE = "rag_answer_generation"

    def __init__(
        self,
        *,
        prompt_service: PromptService,
        model_gateway: ModelGateway,
    ) -> None:
        self.prompt_service = prompt_service
        self.model_gateway = model_gateway

    async def generate(
        self,
        db: AsyncSession,
        *,
        tenant_id: UUID,
        question: str,
        context: str,
        citation_rules: str | None = None,
        request_id: str | None = None,
        user_id: UUID | None = None,
    ) -> RagAnswerResult:
        """
        生成 RAG 回答。
        """

        render_result = await self.prompt_service.render_prompt(
            db,
            payload=PromptRenderRequest(
                tenant_id=tenant_id,
                scene=self.RAG_PROMPT_SCENE,
                variables={
                    "question": question,
                    "context": context,
                    "citation_rules": citation_rules or self._default_citation_rules(),
                },
            ),
        )

        model_config = render_result.model_config_json or {}

        provider = self._get_optional_str(model_config, "provider")
        model = self._get_optional_str(model_config, "model")
        temperature = self._get_optional_float(
            model_config,
            "temperature",
            default=0.2,
        )
        max_tokens = self._get_optional_int(model_config, "max_tokens")

        extra_body = model_config.get("extra_body")
        if not isinstance(extra_body, dict):
            extra_body = None

        response = await self.model_gateway.chat(
            ChatRequest(
                tenant_id=tenant_id,
                user_id=user_id,
                request_id=request_id,
                prompt_template_id=render_result.template_id,
                prompt_version_id=render_result.version_id,
                provider=provider,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                extra_body=extra_body,
                messages=[
                    LLMMessage(
                        role="user",
                        content=render_result.rendered_content,
                    )
                ],
            )
        )

        return RagAnswerResult(
            answer=response.content,
            prompt_template_id=render_result.template_id,
            prompt_version_id=render_result.version_id,
            model_provider=response.provider,
            model_name=response.model_name,
        )

    @staticmethod
    def _default_citation_rules() -> str:
        return (
            "请严格基于给定 context 回答。"
            "如果 context 中没有足够依据，请明确说明知识库中没有找到可靠依据。"
            "回答涉及企业政策、售后规则、价格、流程时，必须依据引用内容，不要编造。"
        )

    @staticmethod
    def _get_optional_str(
        model_config: dict[str, Any],
        key: str,
    ) -> str | None:
        value = model_config.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None

    @staticmethod
    def _get_optional_float(
        model_config: dict[str, Any],
        key: str,
        *,
        default: float,
    ) -> float:
        value = model_config.get(key)

        if value is None:
            return default

        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _get_optional_int(
        model_config: dict[str, Any],
        key: str,
    ) -> int | None:
        value = model_config.get(key)

        if value is None:
            return None

        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return None

        return parsed if parsed > 0 else None