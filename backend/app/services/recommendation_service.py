# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/05/03 14:21
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
import re
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID

from app.schemas.shopping_guide import (
    ShoppingGuideBudget,
    ShoppingGuideBudgetMatch,
    ShoppingGuideComparisonItem,
    ShoppingGuideMatchEvidence,
    ShoppingGuideNeed,
    ShoppingGuidePreferenceMatch,
    ShoppingGuideRecommendationItem,
    ShoppingGuideReviewRisk,
    ShoppingGuideReviewSummary,
    ShoppingGuideScenarioMatch,
    ShoppingGuideSkuView,
    ShoppingGuideStockRisk,
)
from app.services.product_service import ProductService
from app.services.user_service import UserService


class RecommendationService:
    """智能导购推荐服务。

    边界：
    - 可以调用 ProductService / UserService。
    - 不直接查数据库。
    - 不相信 LLM 编造的商品、SKU、价格、库存。
    - 推荐依据必须由结构化规则生成。
    """

    SCENARIO_KEYWORDS: dict[str, list[str]] = {
        "office": ["办公室", "办公", "公司", "工位"],
        "home": ["家用", "家庭", "客厅", "卧室"],
        "dorm": ["宿舍", "学生", "寝室"],
        "travel": ["出差", "旅行", "便携", "旅游"],
        "gift": ["送礼", "礼物", "生日", "节日"],
        "commute": ["通勤", "地铁", "公交"],
        "sport": ["运动", "跑步", "健身"],
    }

    PREFERENCE_KEYWORDS: dict[str, list[str]] = {
        "安全": ["安全", "放心", "保护", "防烫", "恒温"],
        "省心": ["省心", "方便", "自动", "智能", "简单"],
        "便携": ["便携", "轻便", "小巧", "随身"],
        "静音": ["静音", "安静", "低噪"],
        "续航": ["续航", "电池", "耐用"],
        "降噪": ["降噪", "隔音"],
        "性价比": ["性价比", "划算", "便宜", "实惠"],
        "颜值": ["颜值", "好看", "设计", "外观"],
        "大容量": ["大容量", "容量大"],
        "易清洁": ["易清洁", "好清洗", "清洗方便"],
        "售后好": ["售后", "客服", "保修"],
        "评价好": ["评价好", "口碑", "好评"],
    }

    PREFERENCE_DISPLAY_MAP: dict[str, str] = {
        "smart_home": "智能家居",
        "kitchen": "厨房场景",
        "medium": "中等预算",
    }

    def __init__(
            self,
            product_service: ProductService | None = None,
            user_service: UserService | None = None,
    ) -> None:
        self.product_service = product_service or ProductService()
        self.user_service = user_service or UserService()

    async def parse_user_need(
            self,
            *,
            message: str,
            context: dict[str, Any] | None = None,
    ) -> ShoppingGuideNeed:
        context = context or {}

        budget = self._parse_budget(message, context)
        scenario = self._parse_scenario(message, context)
        preferences = self._parse_preferences(message, context)
        keywords = self._extract_keywords(message)

        product_no = context.get("product_no")
        sku_no = context.get("sku_no")

        return ShoppingGuideNeed(
            user_need=message,
            budget=budget,
            scenario=scenario,
            preferences=preferences,
            product_no=product_no,
            sku_no=sku_no,
            keywords=keywords,
        )

    async def build_user_preference(
            self,
            db: Any,
            *,
            tenant_id: UUID,
            user_no: str | None,
            parsed_need: ShoppingGuideNeed,
    ) -> list[str]:
        preferences = list(parsed_need.preferences)

        if not user_no:
            return preferences

        try:
            user_profile = await self.user_service.get_user_profile(
                db,
                tenant_id=tenant_id,
                user_no=user_no,
            )
        except Exception:
            return preferences

        preference_json = self._get_value(user_profile, "preference_json", {}) or {}
        tag_json = self._get_value(user_profile, "tag_json", {}) or {}

        for source in (preference_json, tag_json):
            if isinstance(source, dict):
                for value in source.values():
                    if isinstance(value, str):
                        preferences.append(value)
                    elif isinstance(value, list):
                        preferences.extend(str(item) for item in value)

        return self._dedupe_keep_order(preferences)

    async def build_structured_recommendations(
            self,
            db: Any,
            *,
            tenant_id: UUID,
            parsed_need: ShoppingGuideNeed,
            user_preferences: list[str] | None = None,
            limit: int = 5,
    ) -> tuple[list[ShoppingGuideRecommendationItem], list[ShoppingGuideComparisonItem]]:
        user_preferences = user_preferences or parsed_need.preferences

        if parsed_need.product_no:
            product = await self._get_active_product_detail(
                db,
                tenant_id=tenant_id,
                product_no=parsed_need.product_no,
            )
            products = [product] if product is not None else []
        else:
            products = await self._list_active_products(
                db,
                tenant_id=tenant_id,
                keyword=self._guess_product_keyword(parsed_need),
            )

        recommendations: list[ShoppingGuideRecommendationItem] = []
        comparisons: list[ShoppingGuideComparisonItem] = []

        for product in products:
            product_no = self._get_value(product, "product_no")
            title = self._get_value(product, "title", "")
            status = self._get_value(product, "status")

            # ProductService.list_products 用户侧已经只返回 active 商品。
            # 如果响应 schema 不包含 status，则信任 ProductService 的过滤结果。
            if not product_no:
                continue

            if status is not None and status != "active":
                continue

            skus = await self._list_active_skus(
                db,
                tenant_id=tenant_id,
                product_no=product_no,
            )

            sku_views = [
                self._build_sku_view(sku, parsed_need.budget)
                for sku in skus
                if self._is_active_or_status_missing(sku)
            ]

            sku_views = [sku for sku in sku_views if sku.stock_quantity > 0]

            if parsed_need.budget and parsed_need.budget.max_price is not None:
                sku_views = [
                    sku for sku in sku_views
                    if sku.sale_price <= parsed_need.budget.max_price
                ]

            if not sku_views:
                continue

            reviews = await self._list_visible_reviews(
                db,
                tenant_id=tenant_id,
                product_no=product_no,
            )
            review_summary = self._summarize_reviews(reviews)

            evidence = self._build_match_evidence(
                product=product,
                sku_views=sku_views,
                parsed_need=parsed_need,
                user_preferences=user_preferences,
                review_summary=review_summary,
            )

            risk_notes = self._build_risk_notes(evidence)

            recommendation_reason = self._build_rule_based_reason(
                product_title=title,
                evidence=evidence,
                sku_views=sku_views,
            )

            recommendation = ShoppingGuideRecommendationItem(
                product_no=product_no,
                title=title,
                brand=self._get_value(product, "brand"),
                category=self._get_value(product, "category"),
                matched_skus=sku_views,
                review_summary=review_summary,
                match_evidence=evidence,
                recommendation_reason=recommendation_reason,
                risk_notes=risk_notes,
            )

            recommendations.append(recommendation)

            comparisons.append(
                ShoppingGuideComparisonItem(
                    product_no=product_no,
                    title=title,
                    skus=sku_views,
                )
            )

            if len(recommendations) >= limit:
                break

        recommendations.sort(key=self._recommendation_sort_key, reverse=True)

        return recommendations, comparisons

    def build_fallback_answer(
            self,
            *,
            parsed_need: ShoppingGuideNeed,
            recommendations: list[ShoppingGuideRecommendationItem],
    ) -> str:
        if not recommendations:
            parts = ["我暂时没有找到完全匹配的在售商品。"]
            if parsed_need.budget and parsed_need.budget.max_price:
                parts.append(
                    f"你当前预算上限是 {parsed_need.budget.max_price} 元，可以补充更明确的品类或放宽预算后再试。")
            parts.append("可以补充一下使用场景、预算范围或偏好，我再帮你缩小选择。")
            return "".join(parts)

        top = recommendations[0]
        sku_text = ""
        if top.matched_skus:
            sku = top.matched_skus[0]
            sku_text = f" 推荐 SKU 是 {sku.sku_name or sku.sku_no}，价格 {sku.sale_price} 元，库存 {sku.stock_quantity}。"

        risks = ""
        if top.risk_notes:
            risks = " 需要注意：" + "；".join(top.risk_notes)

        return (
            f"我更推荐你优先看「{top.title}」。"
            f"{top.recommendation_reason}"
            f"{sku_text}"
            f"{risks}"
        )

    def _parse_budget(
            self,
            message: str,
            context: dict[str, Any],
    ) -> ShoppingGuideBudget | None:
        if context.get("budget_max") is not None:
            return ShoppingGuideBudget(
                max_price=self._to_decimal(context["budget_max"]),
                raw_text=str(context["budget_max"]),
            )

        patterns = [
            r"预算\s*(\d+(?:\.\d+)?)",
            r"(\d+(?:\.\d+)?)\s*元?以内",
            r"不超过\s*(\d+(?:\.\d+)?)",
            r"(\d+(?:\.\d+)?)\s*以下",
        ]

        for pattern in patterns:
            matched = re.search(pattern, message)
            if matched:
                value = self._to_decimal(matched.group(1))
                return ShoppingGuideBudget(max_price=value, raw_text=matched.group(0))

        range_match = re.search(r"(\d+(?:\.\d+)?)\s*[-~到至]\s*(\d+(?:\.\d+)?)", message)
        if range_match:
            return ShoppingGuideBudget(
                min_price=self._to_decimal(range_match.group(1)),
                max_price=self._to_decimal(range_match.group(2)),
                raw_text=range_match.group(0),
            )

        if "便宜" in message or "实惠" in message or "性价比" in message:
            return ShoppingGuideBudget(max_price=Decimal("300"), raw_text="便宜/实惠/性价比")

        return None

    def _parse_scenario(self, message: str, context: dict[str, Any]) -> str | None:
        if context.get("scenario"):
            return str(context["scenario"])

        for scenario, keywords in self.SCENARIO_KEYWORDS.items():
            if any(keyword in message for keyword in keywords):
                return scenario

        return None

    def _parse_preferences(self, message: str, context: dict[str, Any]) -> list[str]:
        preferences: list[str] = []

        context_preferences = context.get("preferences") or []
        if isinstance(context_preferences, str):
            preferences.append(context_preferences)
        elif isinstance(context_preferences, list):
            preferences.extend(str(item) for item in context_preferences)

        for preference, keywords in self.PREFERENCE_KEYWORDS.items():
            if any(keyword in message for keyword in keywords):
                preferences.append(preference)

        return self._dedupe_keep_order(preferences)

    def _extract_keywords(self, message: str) -> list[str]:
        candidates = []
        for word in ["电热水壶", "水壶", "耳机", "香薰机", "小家电", "智能"]:
            if word in message:
                candidates.append(word)
        return self._dedupe_keep_order(candidates)

    def _guess_product_keyword(self, parsed_need: ShoppingGuideNeed) -> str | None:
        """只用明确商品词做 keyword，避免“小家电/智能”这类宽泛词误杀候选。"""

        specific_keywords = [
            keyword
            for keyword in parsed_need.keywords
            if keyword not in {"小家电", "智能"}
        ]

        if specific_keywords:
            return specific_keywords[0]

        return None

    async def _list_active_products(
            self,
            db: Any,
            *,
            tenant_id: UUID,
            keyword: str | None = None,
    ) -> list[Any]:
        result = await self.product_service.list_products(
            db,
            tenant_id=tenant_id,
            keyword=keyword,
            page=1,
            page_size=50,
        )
        items = self._extract_items(result)

        # 关键修正：
        # 如果 keyword 搜不到，不直接判空，而是回退到 active 商品池。
        # 预算、库存、inactive、SKU 状态仍然由后续规则严格过滤。
        if keyword and not items:
            fallback_result = await self.product_service.list_products(
                db,
                tenant_id=tenant_id,
                keyword=None,
                page=1,
                page_size=50,
            )
            items = self._extract_items(fallback_result)

        return items

    async def _list_active_skus(
            self,
            db: Any,
            *,
            tenant_id: UUID,
            product_no: str,
    ) -> list[Any]:
        result = await self.product_service.list_product_skus(
            db,
            tenant_id=tenant_id,
            product_no=product_no,
        )
        return self._extract_items(result)

    async def _list_visible_reviews(
            self,
            db: Any,
            *,
            tenant_id: UUID,
            product_no: str,
    ) -> list[Any]:
        try:
            result = await self.product_service.list_product_reviews(
                db,
                tenant_id=tenant_id,
                product_no=product_no,
                page=1,
                page_size=20,
            )
        except TypeError:
            result = await self.product_service.list_product_reviews(
                db,
                tenant_id=tenant_id,
                product_no=product_no,
            )
        return self._extract_items(result)

    async def _get_active_product_detail(
            self,
            db: Any,
            *,
            tenant_id: UUID,
            product_no: str,
    ) -> Any | None:
        try:
            return await self.product_service.get_product_detail(
                db,
                tenant_id=tenant_id,
                product_no=product_no,
            )
        except Exception:
            return None

    def _build_sku_view(
            self,
            sku: Any,
            budget: ShoppingGuideBudget | None,
    ) -> ShoppingGuideSkuView:
        sale_price = self._to_decimal(self._get_value(sku, "sale_price", "0"))
        stock_quantity = int(self._get_value(sku, "stock_quantity", 0) or 0)
        within_budget = None

        if budget and budget.max_price is not None:
            within_budget = sale_price <= budget.max_price

        return ShoppingGuideSkuView(
            sku_no=self._get_value(sku, "sku_no"),
            sku_name=self._get_value(sku, "sku_name"),
            sale_price=sale_price,
            stock_quantity=stock_quantity,
            status=self._get_value(sku, "status") or "active",
            spec_json=self._get_value(sku, "spec_json", {}) or {},
            within_budget=within_budget,
            stock_risk_level=self._stock_risk_level(stock_quantity),
        )

    def _summarize_reviews(self, reviews: list[Any]) -> ShoppingGuideReviewSummary:
        positive_reviews: list[str] = []
        negative_reviews: list[str] = []
        ratings: list[float] = []

        for review in reviews:
            rating = self._get_value(review, "rating")
            sentiment = self._get_value(review, "sentiment")
            content = self._get_value(review, "content", "")

            if rating is not None:
                try:
                    ratings.append(float(rating))
                except (TypeError, ValueError):
                    pass

            if sentiment == "negative" or (rating is not None and float(rating) <= 2):
                if content:
                    negative_reviews.append(content)
            elif sentiment == "positive" or (rating is not None and float(rating) >= 4):
                if content:
                    positive_reviews.append(content)

        average_rating = round(sum(ratings) / len(ratings), 2) if ratings else None

        if positive_reviews and not negative_reviews:
            summary = "当前可见评价整体偏正向。"
        elif positive_reviews and negative_reviews:
            summary = "当前可见评价有正向反馈，也存在需要注意的负面反馈。"
        elif negative_reviews:
            summary = "当前可见评价存在负面反馈，建议谨慎选择。"
        else:
            summary = "当前可见评价较少，建议结合价格、库存和规格一起判断。"

        return ShoppingGuideReviewSummary(
            positive_count=len(positive_reviews),
            negative_count=len(negative_reviews),
            average_rating=average_rating,
            representative_positive_reviews=positive_reviews[:2],
            representative_negative_reviews=negative_reviews[:2],
            summary=summary,
        )

    def _build_match_evidence(
            self,
            *,
            product: Any,
            sku_views: list[ShoppingGuideSkuView],
            parsed_need: ShoppingGuideNeed,
            user_preferences: list[str],
            review_summary: ShoppingGuideReviewSummary,
    ) -> ShoppingGuideMatchEvidence:
        min_price = min((sku.sale_price for sku in sku_views), default=Decimal("0"))

        if parsed_need.budget and parsed_need.budget.max_price is not None:
            budget_matched = min_price <= parsed_need.budget.max_price
            budget_reason = (
                f"最低匹配 SKU 售价 {min_price}，"
                f"{'低于或等于' if budget_matched else '高于'}预算上限 {parsed_need.budget.max_price}。"
            )
        else:
            budget_matched = True
            budget_reason = "用户未给出明确预算，本轮不按预算排除。"

        product_text = self._product_search_text(product)
        scenario_matched = False
        if parsed_need.scenario:
            scenario_keywords = self.SCENARIO_KEYWORDS.get(parsed_need.scenario, [])
            scenario_matched = any(keyword in product_text for keyword in scenario_keywords)
            scenario_reason = (
                f"商品信息与 {parsed_need.scenario} 场景存在匹配。"
                if scenario_matched
                else f"商品信息未明显命中 {parsed_need.scenario} 场景，但仍可作为候选。"
            )
        else:
            scenario_matched = True
            scenario_reason = "用户未给出明确使用场景，本轮不按场景排除。"

        matched_preferences = []
        for preference in user_preferences:
            keywords = self.PREFERENCE_KEYWORDS.get(preference, [preference])
            if any(keyword in product_text for keyword in keywords):
                matched_preferences.append(preference)

        preference_matched = bool(matched_preferences) if user_preferences else True
        display_matched_preferences = [
            self._display_preference(preference)
            for preference in matched_preferences
        ]

        preference_reason = (
            f"命中偏好：{', '.join(display_matched_preferences)}。"
            if display_matched_preferences
            else "未明显命中偏好，但商品仍满足基础候选条件。"
        )

        min_stock = min((sku.stock_quantity for sku in sku_views), default=0)
        stock_level = self._stock_risk_level(min_stock)
        stock_reason = self._stock_risk_reason(min_stock)

        review_level = "low"
        if review_summary.negative_count > 0:
            review_level = "medium"
        if review_summary.negative_count > review_summary.positive_count:
            review_level = "high"

        review_reason = review_summary.summary

        return ShoppingGuideMatchEvidence(
            budget_match=ShoppingGuideBudgetMatch(
                matched=budget_matched,
                reason=budget_reason,
            ),
            scenario_match=ShoppingGuideScenarioMatch(
                matched=scenario_matched,
                reason=scenario_reason,
            ),
            preference_match=ShoppingGuidePreferenceMatch(
                matched=preference_matched,
                matched_preferences=display_matched_preferences,
                reason=preference_reason,
            ),
            stock_risk=ShoppingGuideStockRisk(
                level=stock_level,
                reason=stock_reason,
            ),
            review_risk=ShoppingGuideReviewRisk(
                level=review_level,
                reason=review_reason,
            ),
        )

    def _build_rule_based_reason(
            self,
            *,
            product_title: str,
            evidence: ShoppingGuideMatchEvidence,
            sku_views: list[ShoppingGuideSkuView],
    ) -> str:
        best_sku = min(sku_views, key=lambda sku: sku.sale_price)

        parts = [
            f"{product_title} 的最低可选 SKU 价格为 {best_sku.sale_price} 元。",
            evidence.budget_match.reason,
            evidence.scenario_match.reason,
            evidence.preference_match.reason,
            evidence.stock_risk.reason,
            evidence.review_risk.reason,
        ]

        return "".join(parts)

    def _build_risk_notes(self, evidence: ShoppingGuideMatchEvidence) -> list[str]:
        notes: list[str] = []

        if not evidence.budget_match.matched:
            notes.append(evidence.budget_match.reason)

        if evidence.stock_risk.level in {"low_stock", "out_of_stock"}:
            notes.append(evidence.stock_risk.reason)

        if evidence.review_risk.level in {"medium", "high"}:
            notes.append(evidence.review_risk.reason)

        return notes

    def _recommendation_sort_key(self, item: ShoppingGuideRecommendationItem) -> tuple[int, int, int, int]:
        evidence = item.match_evidence
        return (
            int(evidence.budget_match.matched),
            int(evidence.scenario_match.matched),
            int(evidence.preference_match.matched),
            -len(item.risk_notes),
        )

    def _stock_risk_level(self, stock_quantity: int) -> str:
        if stock_quantity <= 0:
            return "out_of_stock"
        if stock_quantity <= 3:
            return "low_stock"
        return "normal"

    def _stock_risk_reason(self, stock_quantity: int) -> str:
        if stock_quantity <= 0:
            return "当前库存为 0，不应推荐。"
        if stock_quantity <= 3:
            return f"库存仅剩 {stock_quantity}，存在低库存风险。"
        return f"库存 {stock_quantity}，暂无明显库存风险。"

    def _product_search_text(self, product: Any) -> str:
        fields = [
            self._get_value(product, "title", ""),
            self._get_value(product, "subtitle", ""),
            self._get_value(product, "description", ""),
            self._get_value(product, "brand", ""),
            self._get_value(product, "category", ""),
            self._get_value(product, "category_path", ""),
            str(self._get_value(product, "tag_json", "") or ""),
            str(self._get_value(product, "attribute_json", "") or ""),
            str(self._get_value(product, "metadata_json", "") or ""),
        ]
        return " ".join(str(field) for field in fields if field)

    def _extract_items(self, result: Any) -> list[Any]:
        """从 service 返回值中提取列表。

        兼容以下结构：
        - list
        - {"items": [...]}
        - {"data": [...]}
        - {"data": {"items": [...]}}
        - Pydantic 对象：items 字段
        - Pydantic 对象：data 字段
        - Pydantic 对象：model_dump() 后再递归提取
        """

        if result is None:
            return []

        if isinstance(result, list):
            return result

        if isinstance(result, dict):
            items = result.get("items")
            if isinstance(items, list):
                return items

            data = result.get("data")
            if isinstance(data, list):
                return data
            if data is not None:
                return self._extract_items(data)

            return []

        items = getattr(result, "items", None)
        if isinstance(items, list):
            return items

        data = getattr(result, "data", None)
        if data is not None:
            return self._extract_items(data)

        model_dump = getattr(result, "model_dump", None)
        if callable(model_dump):
            try:
                return self._extract_items(model_dump(mode="python"))
            except TypeError:
                return self._extract_items(model_dump())

        dict_method = getattr(result, "dict", None)
        if callable(dict_method):
            try:
                return self._extract_items(dict_method())
            except TypeError:
                return []

        return []

    def _get_value(self, obj: Any, key: str, default: Any = None) -> Any:
        if obj is None:
            return default
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    def _to_decimal(self, value: Any) -> Decimal:
        try:
            return Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            return Decimal("0")

    def _dedupe_keep_order(self, values: list[str]) -> list[str]:
        seen = set()
        result = []
        for value in values:
            if value and value not in seen:
                seen.add(value)
                result.append(value)
        return result

    def _is_active_or_status_missing(self, obj: Any) -> bool:
        """用户侧 ProductService 已做 active 过滤；schema 不带 status 时不能误杀。"""
        status = self._get_value(obj, "status")
        return status is None or status == "active"

    def _display_preference(self, preference: str) -> str:
        return self.PREFERENCE_DISPLAY_MAP.get(preference, preference)
