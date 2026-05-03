# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/28 17:45
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field


ModelType = Literal["llm", "embedding", "rerank"]
CallType = Literal["chat", "completion", "embedding", "rerank", "stream_chat"]
ModelCallStatus = Literal["success", "failed", "timeout", "canceled"]


class LLMMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"] = Field(
        ...,
        description="消息角色",
    )
    content: str = Field(
        ...,
        min_length=1,
        description="消息内容",
    )


class TokenUsage(BaseModel):
    input_tokens: int | None = Field(default=None, description="输入 token 数")
    output_tokens: int | None = Field(default=None, description="输出 token 数")
    total_tokens: int | None = Field(default=None, description="总 token 数")


class ModelCallContext(BaseModel):
    tenant_id: uuid.UUID = Field(..., description="租户 ID")
    user_id: uuid.UUID | None = Field(default=None, description="用户 ID")
    request_id: str | None = Field(default=None, description="请求追踪 ID")
    prompt_template_id: uuid.UUID | None = Field(default=None, description="Prompt 模板 ID")
    prompt_version_id: uuid.UUID | None = Field(default=None, description="Prompt 版本 ID")


class ChatRequest(ModelCallContext):
    provider: str | None = Field(default=None, description="模型 Provider")
    model: str | None = Field(default=None, description="模型名称")
    messages: list[LLMMessage] = Field(..., min_length=1, description="聊天消息")
    temperature: float | None = Field(default=0.7, ge=0, le=2, description="采样温度")
    max_tokens: int | None = Field(default=None, gt=0, description="最大输出 token")
    extra_body: dict[str, Any] | None = Field(default=None, description="Provider 扩展参数")


class ChatResponse(BaseModel):
    provider: str = Field(..., description="模型 Provider")
    model_name: str = Field(..., description="模型名称")
    content: str = Field(..., description="模型输出文本")
    usage: TokenUsage = Field(default_factory=TokenUsage, description="Token 用量")
    latency_ms: int | None = Field(default=None, description="调用耗时")
    raw_response_id: str | None = Field(default=None, description="Provider 返回 ID")


class EmbeddingRequest(ModelCallContext):
    provider: str | None = Field(default=None, description="模型 Provider")
    model: str | None = Field(default=None, description="Embedding 模型名称")
    texts: list[str] = Field(..., min_length=1, description="待向量化文本")
    extra_body: dict[str, Any] | None = Field(default=None, description="Provider 扩展参数")


class EmbeddingResponse(BaseModel):
    provider: str = Field(..., description="模型 Provider")
    model_name: str = Field(..., description="模型名称")
    embeddings: list[list[float]] = Field(..., description="向量结果")
    usage: TokenUsage = Field(default_factory=TokenUsage, description="Token 用量")
    latency_ms: int | None = Field(default=None, description="调用耗时")
    raw_response_id: str | None = Field(default=None, description="Provider 返回 ID")