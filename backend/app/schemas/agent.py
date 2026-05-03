# -*- coding: utf-8 -*-
"""
创建时间    :2026/05/02 19:31
IDE       :PyCharm
作者      :董宏升
"""

# 每次解决问题，我都在成长，不要着急，不要气馁！
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class AgentToolCallView(BaseModel):
    """客服 Agent 对外返回的工具调用摘要。"""

    tool_name: str = Field(..., description="工具名称")
    success: bool = Field(..., description="工具是否调用成功")
    error_code: str | None = Field(default=None, description="失败错误码")
    error_message: str | None = Field(default=None, description="失败错误信息")


class AgentCitationView(BaseModel):
    """RAG 引用来源摘要。"""

    document_id: UUID | None = Field(default=None, description="知识库文档 ID")
    document_title: str | None = Field(default=None, description="知识库文档标题")
    chunk_id: UUID | None = Field(default=None, description="知识库切片 ID")
    chunk_no: int | None = Field(default=None, description="切片编号")
    page_no: int | None = Field(default=None, description="页码")
    section_title: str | None = Field(default=None, description="章节标题")
    score: float | None = Field(default=None, description="检索得分")
    content_snippet: str | None = Field(default=None, description="引用片段")


class AgentStepView(BaseModel):
    """客服 Agent 步骤摘要，主要用于调试和后台展示。"""

    step_name: str = Field(..., description="步骤名称")
    status: str = Field(..., description="步骤状态")
    latency_ms: int | None = Field(default=None, description="步骤耗时，单位毫秒")


class CustomerServiceChatRequest(BaseModel):
    """智能客服对话请求。"""

    tenant_id: UUID = Field(..., description="租户 ID")
    session_id: str = Field(..., min_length=1, max_length=128, description="客服会话 ID")

    user_no: str | None = Field(default=None, max_length=64, description="用户业务编号")
    user_id: UUID | None = Field(default=None, description="用户 ID，认证未完成前可为空")

    message: str = Field(..., min_length=1, max_length=4000, description="用户本轮输入")
    conversation_summary: str | None = Field(
        default=None,
        max_length=8000,
        description="多轮会话摘要，第一版由调用方显式传入",
    )
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="业务上下文，例如 order_no、product_no、after_sale_ticket_no",
    )


class CustomerServiceChatResponse(BaseModel):
    """智能客服对话响应 data。"""

    session_id: str = Field(..., description="客服会话 ID")
    agent_task_id: UUID | None = Field(default=None, description="Agent 任务 ID")

    intent: str = Field(..., description="识别出的客服意图")
    answer: str = Field(..., description="最终回复内容")

    handoff_required: bool = Field(default=False, description="是否需要转人工")
    handoff_reason: str | None = Field(default=None, description="转人工原因")

    tool_calls: list[AgentToolCallView] = Field(
        default_factory=list,
        description="本轮 Agent 工具调用摘要",
    )
    citations: list[AgentCitationView] = Field(
        default_factory=list,
        description="RAG 引用来源",
    )
    steps: list[AgentStepView] = Field(
        default_factory=list,
        description="Agent 步骤摘要，主要用于调试和后台展示",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="扩展信息，例如 confidence、entities 等",
    )