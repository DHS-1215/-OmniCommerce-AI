from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


ContentType = Literal[
    "product_title",
    "product_selling_points",
    "product_detail",
    "campaign_copy",
]

BizType = Literal[
    "product",
    "campaign",
]

ContentAssetStatus = Literal[
    "draft",
    "reviewing",
    "approved",
    "rejected",
    "archived",
]

ContentReviewStatus = Literal[
    "pending",
    "passed",
    "failed",
    "manual_required",
]

ContentReviewType = Literal[
    "rule_check",
    "model_review",
    "manual_review",
]

ReviewerType = Literal[
    "system",
    "model",
    "human",
]


class SensitiveCheckResult(BaseModel):
    passed: bool
    matched_words: list[str] = Field(default_factory=list)
    risk_level: Literal["low", "medium", "high"] = "low"
    suggestion: str | None = None


class BrandCheckResult(BaseModel):
    passed: bool
    violations: list[str] = Field(default_factory=list)
    risk_level: Literal["low", "medium", "high"] = "low"
    suggestion: str | None = None


class RuleCheckResult(BaseModel):
    passed: bool
    review_status: Literal["passed", "failed", "manual_required"]
    risk_level: Literal["low", "medium", "high"]
    sensitive_check: SensitiveCheckResult
    brand_check: BrandCheckResult


class ContentGenerateBaseRequest(BaseModel):
    tenant_id: UUID
    requirements: str | None = Field(default=None, max_length=2000)
    tone: str | None = Field(default=None, max_length=255)
    created_by: str | None = Field(default=None, max_length=128)
    metadata_json: dict[str, Any] | None = None


class ProductContentGenerateRequest(ContentGenerateBaseRequest):
    product_no: str = Field(min_length=1, max_length=64)


class CampaignContentGenerateRequest(ContentGenerateBaseRequest):
    campaign_name: str = Field(min_length=1, max_length=255)
    campaign_context: dict[str, Any] = Field(default_factory=dict)


class ContentReviewRequest(BaseModel):
    tenant_id: UUID
    content: str = Field(min_length=1)
    brand: str | None = Field(default=None, max_length=128)
    content_type: ContentType
    enable_model_review: bool = False
    reviewer_id: str | None = Field(default=None, max_length=128)


class ContentSubmitReviewRequest(BaseModel):
    tenant_id: UUID
    operator_id: str | None = Field(default=None, max_length=128)
    comments: str | None = Field(default=None, max_length=2000)


class ContentManualReviewRequest(BaseModel):
    tenant_id: UUID
    reviewer_id: str | None = Field(default=None, max_length=128)
    comments: str | None = Field(default=None, max_length=2000)


class ContentAssetResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    asset_group_id: UUID
    version: int
    content_type: str
    biz_type: str
    biz_id: str | None
    title: str | None
    content: str
    status: str
    review_status: str
    source: str
    prompt_template_id: UUID | None
    prompt_version_id: UUID | None
    model_call_log_id: UUID | None
    generation_input_json: dict[str, Any] | None
    generation_output_json: dict[str, Any] | None
    rule_check_result_json: dict[str, Any] | None
    metadata_json: dict[str, Any] | None
    created_by: str | None
    approved_by: str | None
    approved_at: datetime | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None

    model_config = {
        "from_attributes": True,
    }


class ContentReviewResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    content_asset_id: UUID
    review_type: str
    review_status: str
    reviewer_type: str
    reviewer_id: str | None
    sensitive_check_result_json: dict[str, Any] | None
    brand_check_result_json: dict[str, Any] | None
    model_review_result_json: dict[str, Any] | None
    comments: str | None
    request_id: str | None
    created_at: datetime

    model_config = {
        "from_attributes": True,
    }


class ContentGenerateResponse(BaseModel):
    asset: ContentAssetResponse
    review: ContentReviewResponse | None = None
    rule_check: RuleCheckResult


class ContentReviewOnlyResponse(BaseModel):
    rule_check: RuleCheckResult
    model_review_result_json: dict[str, Any] | None = None


class ContentVersionListResponse(BaseModel):
    asset_group_id: UUID
    items: list[ContentAssetResponse]
    total: int
