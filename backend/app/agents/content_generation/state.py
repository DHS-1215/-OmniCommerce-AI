from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ContentGenerationState(BaseModel):
    """内容生成轻量受控编排状态。

    这里不是自由 Agent，只记录 generate -> review -> persist 的受控流程状态。
    """

    tenant_id: UUID
    content_type: str
    biz_type: str
    biz_id: str | None = None

    variables: dict[str, Any] = Field(default_factory=dict)
    rendered_prompt: str | None = None

    generated_content: str | None = None
    title: str | None = None

    prompt_template_id: UUID | None = None
    prompt_version_id: UUID | None = None
    model_call_log_id: UUID | None = None

    rule_check_result: dict[str, Any] | None = None
    content_asset_id: UUID | None = None
    content_review_id: UUID | None = None

    status: str = "initialized"
    error_message: str | None = None
