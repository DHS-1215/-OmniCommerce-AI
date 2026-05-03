# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/05/03 14:13
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ShoppingGuideChatRequest(BaseModel):
    tenant_id: UUID
    session_id: str
    user_no: str | None = None
    message: str
    conversation_summary: str | None = ""
    context: dict[str, Any] = Field(default_factory=dict)


class ShoppingGuideBudget(BaseModel):
    min_price: Decimal | None = None
    max_price: Decimal | None = None
    raw_text: str | None = None


class ShoppingGuideNeed(BaseModel):
    user_need: str
    budget: ShoppingGuideBudget | None = None
    scenario: str | None = None
    preferences: list[str] = Field(default_factory=list)
    product_no: str | None = None
    sku_no: str | None = None
    keywords: list[str] = Field(default_factory=list)


class ShoppingGuideBudgetMatch(BaseModel):
    matched: bool
    reason: str


class ShoppingGuideScenarioMatch(BaseModel):
    matched: bool
    reason: str


class ShoppingGuidePreferenceMatch(BaseModel):
    matched: bool
    matched_preferences: list[str] = Field(default_factory=list)
    reason: str


class ShoppingGuideStockRisk(BaseModel):
    level: str
    reason: str


class ShoppingGuideReviewRisk(BaseModel):
    level: str
    reason: str


class ShoppingGuideMatchEvidence(BaseModel):
    budget_match: ShoppingGuideBudgetMatch
    scenario_match: ShoppingGuideScenarioMatch
    preference_match: ShoppingGuidePreferenceMatch
    stock_risk: ShoppingGuideStockRisk
    review_risk: ShoppingGuideReviewRisk


class ShoppingGuideSkuView(BaseModel):
    sku_no: str
    sku_name: str | None = None
    sale_price: Decimal
    stock_quantity: int
    status: str | None = None
    spec_json: dict[str, Any] = Field(default_factory=dict)
    within_budget: bool | None = None
    stock_risk_level: str | None = None


class ShoppingGuideReviewSummary(BaseModel):
    positive_count: int = 0
    negative_count: int = 0
    average_rating: float | None = None
    representative_positive_reviews: list[str] = Field(default_factory=list)
    representative_negative_reviews: list[str] = Field(default_factory=list)
    summary: str


class ShoppingGuideRecommendationItem(BaseModel):
    product_no: str
    title: str
    brand: str | None = None
    category: str | None = None
    matched_skus: list[ShoppingGuideSkuView] = Field(default_factory=list)
    review_summary: ShoppingGuideReviewSummary | None = None
    match_evidence: ShoppingGuideMatchEvidence
    recommendation_reason: str
    risk_notes: list[str] = Field(default_factory=list)


class ShoppingGuideComparisonItem(BaseModel):
    product_no: str
    title: str
    skus: list[ShoppingGuideSkuView] = Field(default_factory=list)


class ShoppingGuideToolCallView(BaseModel):
    tool_name: str
    success: bool
    error_code: str | None = None
    error_message: str | None = None


class ShoppingGuideCitationView(BaseModel):
    document_id: str | None = None
    document_title: str | None = None
    chunk_id: str | None = None
    page_no: int | None = None
    score: float | None = None
    content_snippet: str | None = None


class ShoppingGuideChatResponse(BaseModel):
    session_id: str
    agent_task_id: UUID | None = None
    intent: str = "shopping_guide"
    answer: str
    budget: ShoppingGuideBudget | None = None
    scenario: str | None = None
    preferences: list[str] = Field(default_factory=list)
    recommendations: list[ShoppingGuideRecommendationItem] = Field(default_factory=list)
    comparisons: list[ShoppingGuideComparisonItem] = Field(default_factory=list)
    tool_calls: list[ShoppingGuideToolCallView] = Field(default_factory=list)
    citations: list[ShoppingGuideCitationView] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
