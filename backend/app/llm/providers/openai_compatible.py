# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/28 18:00
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
import asyncio
import json
import time
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.core.config import Settings, get_settings
from app.core.exceptions import ModelGatewayException
from app.llm.base import BaseModelProvider
from app.llm.schemas import (
    ChatRequest,
    ChatResponse,
    EmbeddingRequest,
    EmbeddingResponse,
    TokenUsage,
)


class OpenAICompatibleProvider(BaseModelProvider):
    """
    OpenAI-compatible Provider。

    支持普通 chat / embeddings 调用。
    对 timeout、network error、5xx 做失败重试。
    400 / 401 / 403 不重试。
    """

    provider_name = "openai_compatible"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.base_url = self.settings.llm_base_url.rstrip("/")
        self.api_key = self.settings.llm_api_key
        self.timeout_seconds = self.settings.llm_timeout_seconds
        self.max_retries = self.settings.llm_max_retries

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            raise ModelGatewayException(
                code="MODEL_PROVIDER_AUTH_MISSING",
                message="LLM_API_KEY is not configured",
            )

        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _usage_from_response(data: dict[str, Any]) -> TokenUsage:
        usage = data.get("usage") or {}
        return TokenUsage(
            input_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
            total_tokens=usage.get("total_tokens"),
        )

    @staticmethod
    def _is_retryable_status(status_code: int) -> bool:
        return status_code >= 500

    @staticmethod
    def _build_http_exception(response: httpx.Response) -> ModelGatewayException:
        message = f"Model provider HTTP error: {response.status_code}"

        try:
            error_body = response.json()
            if isinstance(error_body.get("error"), dict):
                provider_message = error_body["error"].get("message")
                if provider_message:
                    message = provider_message
        except Exception:
            pass

        return ModelGatewayException(
            code="MODEL_PROVIDER_HTTP_ERROR",
            message=message,
            data={
                "status_code": response.status_code,
            },
        )

    async def _request_with_retry(
            self,
            *,
            method: str,
            url: str,
            json_body: dict[str, Any],
    ) -> httpx.Response:
        last_exception: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    response = await client.request(
                        method,
                        url,
                        headers=self._headers(),
                        json=json_body,
                    )

                if response.status_code in {400, 401, 403}:
                    raise self._build_http_exception(response)

                if self._is_retryable_status(response.status_code):
                    if attempt < self.max_retries:
                        await asyncio.sleep(0.2 * (attempt + 1))
                        continue

                    exc = self._build_http_exception(response)
                    exc.data = {
                        **(exc.data or {}),
                        "retry_count": attempt,
                    }
                    raise exc

                response.raise_for_status()
                return response

            except httpx.TimeoutException as exc:
                last_exception = exc
                if attempt < self.max_retries:
                    await asyncio.sleep(0.2 * (attempt + 1))
                    continue

                raise ModelGatewayException(
                    code="MODEL_PROVIDER_TIMEOUT",
                    message="Model provider request timeout",
                    data={
                        "retry_count": attempt,
                    },
                ) from exc

            except httpx.NetworkError as exc:
                last_exception = exc
                if attempt < self.max_retries:
                    await asyncio.sleep(0.2 * (attempt + 1))
                    continue

                raise ModelGatewayException(
                    code="MODEL_PROVIDER_NETWORK_ERROR",
                    message="Model provider network error",
                    data={
                        "retry_count": attempt,
                    },
                ) from exc

            except httpx.HTTPError as exc:
                last_exception = exc
                raise ModelGatewayException(
                    code="MODEL_PROVIDER_HTTP_ERROR",
                    message="Model provider HTTP error",
                    data={
                        "retry_count": attempt,
                    },
                ) from exc

        raise ModelGatewayException(
            code="MODEL_PROVIDER_REQUEST_FAILED",
            message="Model provider request failed",
            data={
                "last_exception": str(last_exception),
            },
        )

    async def chat(self, request: ChatRequest) -> ChatResponse:
        model_name = request.model or self.settings.default_llm_model

        payload: dict[str, Any] = {
            "model": model_name,
            "messages": [message.model_dump() for message in request.messages],
            "stream": False,
        }

        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        if request.extra_body:
            payload.update(request.extra_body)

        start = time.perf_counter()

        try:
            response = await self._request_with_retry(
                method="POST",
                url=f"{self.base_url}/chat/completions",
                json_body=payload,
            )
            data = response.json()
        except json.JSONDecodeError as exc:
            raise ModelGatewayException(
                code="MODEL_PROVIDER_INVALID_RESPONSE",
                message="Model provider returned invalid JSON",
            ) from exc

        try:
            content = data["choices"][0]["message"]["content"]
        except Exception as exc:
            raise ModelGatewayException(
                code="MODEL_PROVIDER_INVALID_RESPONSE",
                message="Model provider response missing choices[0].message.content",
            ) from exc

        latency_ms = int((time.perf_counter() - start) * 1000)

        return ChatResponse(
            provider=self.provider_name,
            model_name=model_name,
            content=content,
            usage=self._usage_from_response(data),
            latency_ms=latency_ms,
            raw_response_id=data.get("id"),
        )

    async def embeddings(self, request: EmbeddingRequest) -> EmbeddingResponse:
        model_name = request.model or self.settings.default_embedding_model

        payload: dict[str, Any] = {
            "model": model_name,
            "input": request.texts,
        }
        if request.extra_body:
            payload.update(request.extra_body)

        start = time.perf_counter()

        try:
            response = await self._request_with_retry(
                method="POST",
                url=f"{self.base_url}/embeddings",
                json_body=payload,
            )
            data = response.json()
        except json.JSONDecodeError as exc:
            raise ModelGatewayException(
                code="MODEL_PROVIDER_INVALID_RESPONSE",
                message="Model provider returned invalid JSON",
            ) from exc

        try:
            embeddings = [item["embedding"] for item in data["data"]]
        except Exception as exc:
            raise ModelGatewayException(
                code="MODEL_PROVIDER_INVALID_RESPONSE",
                message="Model provider response missing embedding data",
            ) from exc

        latency_ms = int((time.perf_counter() - start) * 1000)

        return EmbeddingResponse(
            provider=self.provider_name,
            model_name=model_name,
            embeddings=embeddings,
            usage=self._usage_from_response(data),
            latency_ms=latency_ms,
            raw_response_id=data.get("id"),
        )

    async def stream_chat(self, request: ChatRequest) -> AsyncIterator[str]:
        model_name = request.model or self.settings.default_llm_model

        payload: dict[str, Any] = {
            "model": model_name,
            "messages": [message.model_dump() for message in request.messages],
            "stream": True,
        }

        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        if request.extra_body:
            payload.update(request.extra_body)

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                async with client.stream(
                        "POST",
                        f"{self.base_url}/chat/completions",
                        headers=self._headers(),
                        json=payload,
                ) as response:
                    if response.status_code in {400, 401, 403}:
                        raise self._build_http_exception(response)

                    response.raise_for_status()

                    async for line in response.aiter_lines():
                        if not line or not line.startswith("data:"):
                            continue

                        data_text = line.removeprefix("data:").strip()
                        if data_text == "[DONE]":
                            break

                        try:
                            data = json.loads(data_text)
                        except json.JSONDecodeError:
                            continue

                        delta = (
                            data.get("choices", [{}])[0]
                            .get("delta", {})
                            .get("content")
                        )
                        if delta:
                            yield delta

        except httpx.TimeoutException as exc:
            raise ModelGatewayException(
                code="MODEL_PROVIDER_TIMEOUT",
                message="Model provider stream request timeout",
            ) from exc
        except httpx.NetworkError as exc:
            raise ModelGatewayException(
                code="MODEL_PROVIDER_NETWORK_ERROR",
                message="Model provider stream network error",
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise ModelGatewayException(
                code="MODEL_PROVIDER_HTTP_ERROR",
                message=f"Model provider stream HTTP error: {exc.response.status_code}",
            ) from exc
