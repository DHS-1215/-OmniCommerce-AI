# -*- coding: utf-8 -*-
"""
创建时间    :2026/05/04 11:48
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content_review import ContentReview
from app.repositories.content_review_repository import ContentReviewRepository
from app.schemas.content import BrandCheckResult, RuleCheckResult, SensitiveCheckResult


class ContentReviewService:
    """内容审核服务。

    第一版规则内置在 service 中：
    - 不新增敏感词表；
    - 不新增品牌规则表；
    - 规则审核是必选能力；
    - 模型辅助审核由内容生成服务后续接入。
    """

    def __init__(
            self,
            review_repository: ContentReviewRepository | None = None,
    ) -> None:
        self.review_repository = review_repository or ContentReviewRepository()

    sensitive_words: tuple[str, ...] = (
        "全网第一",
        "最便宜",
        "百分百",
        "100%",
        "绝对安全",
        "永久有效",
        "国家级",
        "顶级",
        "第一品牌",
        "包治",
        "治愈",
        "无副作用",
    )

    absolute_claim_words: tuple[str, ...] = (
        "最高",
        "最低",
        "最佳",
        "最强",
        "第一",
        "唯一",
        "绝对",
        "永久",
        "必然",
        "保证",
    )

    restricted_effect_words: tuple[str, ...] = (
        "治疗",
        "治愈",
        "疗效",
        "降压",
        "减肥",
        "稳赚",
        "保本",
        "法律保证",
    )

    competitor_attack_words: tuple[str, ...] = (
        "吊打竞品",
        "秒杀竞品",
        "碾压竞品",
        "别家都不行",
        "同行垃圾",
    )

    def check_sensitive_words(self, content: str) -> SensitiveCheckResult:
        matched_words = [
            word for word in self.sensitive_words if word.lower() in content.lower()
        ]

        if not matched_words:
            return SensitiveCheckResult(
                passed=True,
                matched_words=[],
                risk_level="low",
                suggestion=None,
            )

        high_risk_words = {"包治", "治愈", "无副作用", "国家级", "全网第一"}
        risk_level = (
            "high"
            if any(word in high_risk_words for word in matched_words)
            else "medium"
        )

        return SensitiveCheckResult(
            passed=False,
            matched_words=matched_words,
            risk_level=risk_level,
            suggestion="命中敏感或高风险表达，建议删除绝对化、医疗化或夸大承诺用语。",
        )

    def check_brand_rules(
            self,
            *,
            content: str,
            brand: str | None,
            content_type: str,
    ) -> BrandCheckResult:
        violations: list[str] = []

        if any(word.lower() in content.lower() for word in self.absolute_claim_words):
            violations.append("存在绝对化营销表达")

        if any(word.lower() in content.lower() for word in self.restricted_effect_words):
            violations.append("存在医疗、金融、法律等效果承诺风险")

        if any(word.lower() in content.lower() for word in self.competitor_attack_words):
            violations.append("存在贬损竞品或不当比较表达")

        if content_type == "product_title":
            if brand and brand.lower() not in content.lower():
                violations.append("商品标题未包含品牌名称")

            if len(content) > 80:
                violations.append("商品标题过长，建议控制在 80 字以内")

        if content_type == "campaign_copy" and len(content) > 2000:
            violations.append("活动文案过长，建议拆分为多个投放素材")

        if not violations:
            return BrandCheckResult(
                passed=True,
                violations=[],
                risk_level="low",
                suggestion=None,
            )

        high_risk_keywords = ("医疗", "金融", "法律", "贬损竞品")
        risk_level = (
            "high"
            if any(any(keyword in violation for keyword in high_risk_keywords) for violation in violations)
            else "medium"
        )

        return BrandCheckResult(
            passed=False,
            violations=violations,
            risk_level=risk_level,
            suggestion="建议按品牌规范重写，避免绝对化、竞品攻击和效果承诺。",
        )

    def run_rule_check(
            self,
            *,
            content: str,
            brand: str | None,
            content_type: str,
    ) -> RuleCheckResult:
        sensitive_check = self.check_sensitive_words(content)
        brand_check = self.check_brand_rules(
            content=content,
            brand=brand,
            content_type=content_type,
        )

        passed = sensitive_check.passed and brand_check.passed

        risk_rank = {
            "low": 1,
            "medium": 2,
            "high": 3,
        }
        risk_level = max(
            [sensitive_check.risk_level, brand_check.risk_level],
            key=lambda item: risk_rank[item],
        )

        if passed:
            review_status = "passed"
        elif risk_level == "high":
            review_status = "failed"
        else:
            review_status = "manual_required"

        return RuleCheckResult(
            passed=passed,
            review_status=review_status,
            risk_level=risk_level,
            sensitive_check=sensitive_check,
            brand_check=brand_check,
        )

    async def create_rule_review_record(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            content_asset_id: UUID,
            rule_check: RuleCheckResult,
            request_id: str | None = None,
            comments: str | None = None,
    ) -> ContentReview:
        review = ContentReview(
            tenant_id=tenant_id,
            content_asset_id=content_asset_id,
            review_type="rule_check",
            review_status=rule_check.review_status,
            reviewer_type="system",
            reviewer_id=None,
            sensitive_check_result_json=rule_check.sensitive_check.model_dump(),
            brand_check_result_json=rule_check.brand_check.model_dump(),
            model_review_result_json=None,
            comments=comments,
            request_id=request_id,
        )

        return await self.review_repository.create(db, review)
