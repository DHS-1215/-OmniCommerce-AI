# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/28 18:01
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from app.core.config import Settings, get_settings
from app.core.exceptions import ModelGatewayException
from app.llm.base import BaseModelProvider
from app.llm.providers.mock import MockProvider
from app.llm.providers.openai_compatible import OpenAICompatibleProvider


class ModelProviderRouter:
    """
    模型 Provider 路由器。

    Chat 和 Embedding 使用独立默认 Provider。
    """

    def __init__(
            self,
            providers: dict[str, BaseModelProvider],
            default_llm_provider_name: str,
            default_embedding_provider_name: str,
    ) -> None:
        self.providers = providers
        self.default_llm_provider_name = default_llm_provider_name
        self.default_embedding_provider_name = default_embedding_provider_name

    def get_chat_provider(self, provider_name: str | None = None) -> BaseModelProvider:
        return self._get_provider(provider_name or self.default_llm_provider_name)

    def get_embedding_provider(
            self,
            provider_name: str | None = None,
    ) -> BaseModelProvider:
        return self._get_provider(provider_name or self.default_embedding_provider_name)

    def _get_provider(self, provider_name: str) -> BaseModelProvider:
        provider = self.providers.get(provider_name)

        if provider is None:
            raise ModelGatewayException(
                code="MODEL_PROVIDER_NOT_FOUND",
                message=f"Model provider not found: {provider_name}",
            )

        return provider


def build_default_provider_router(
        settings: Settings | None = None,
) -> ModelProviderRouter:
    settings = settings or get_settings()

    mock_provider = MockProvider()
    openai_compatible_provider = OpenAICompatibleProvider(settings=settings)

    return ModelProviderRouter(
        providers={
            mock_provider.provider_name: mock_provider,
            openai_compatible_provider.provider_name: openai_compatible_provider,
        },
        default_llm_provider_name=settings.default_llm_provider,
        default_embedding_provider_name=settings.default_embedding_provider,
    )
