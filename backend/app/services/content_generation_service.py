from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.content_generation.state import ContentGenerationState
from app.core.exceptions import BusinessException, NotFoundException
from app.llm.gateway import ModelGateway, build_model_gateway
from app.llm.schemas import ChatRequest, LLMMessage
from app.models.content_asset import ContentAsset
from app.models.llm import ModelCallLog
from app.repositories.content_asset_repository import ContentAssetRepository
from app.repositories.content_review_repository import ContentReviewRepository
from app.schemas.content import (
    CampaignContentGenerateRequest,
    ContentGenerateResponse,
    ProductContentGenerateRequest,
)
from app.schemas.prompt import PromptRenderRequest
from app.services.content_review_service import ContentReviewService
from app.services.model_call_log_service import ModelCallLogService
from app.services.product_service import ProductService
from app.services.prompt_service import PromptService


class ContentGenerationService:
    """内容生成服务。

    负责串联：
    ProductService -> PromptService -> ModelGateway -> ContentReviewService -> 入库。

    约束：
    - 商品相关内容只能通过 ProductService 获取商品信息；
    - Prompt 必须走 PromptService；
    - 模型调用必须走 ModelGateway；
    - 生成结果必须写 content_asset；
    - 规则审核必须写 content_review。
    """

    def __init__(
            self,
            *,
            product_service: ProductService | None = None,
            prompt_service: PromptService | None = None,
            model_gateway: ModelGateway | None = None,
            asset_repository: ContentAssetRepository | None = None,
            review_repository: ContentReviewRepository | None = None,
            review_service: ContentReviewService | None = None,
    ) -> None:
        self.product_service = product_service or ProductService()
        self.prompt_service = prompt_service or PromptService()
        self.model_gateway = model_gateway
        self.asset_repository = asset_repository or ContentAssetRepository()
        self.review_repository = review_repository or ContentReviewRepository()
        self.review_service = review_service or ContentReviewService(
            review_repository=self.review_repository
        )

    async def generate_product_title(
            self,
            db: AsyncSession,
            *,
            request: ProductContentGenerateRequest,
            request_id: str | None = None,
    ) -> ContentGenerateResponse:
        product_context = await self._get_product_context(
            db,
            tenant_id=request.tenant_id,
            product_no=request.product_no,
        )

        state = ContentGenerationState(
            tenant_id=request.tenant_id,
            content_type="product_title",
            biz_type="product",
            biz_id=request.product_no,
            variables=self._build_product_variables(
                content_type="product_title",
                product_context=product_context,
                requirements=request.requirements,
                tone=request.tone,
                output_format="生成 1 个适合电商商品详情页和列表页使用的商品标题。",
            ),
        )

        return await self.generate_content_from_state(
            db,
            state=state,
            created_by=request.created_by,
            metadata_json=request.metadata_json,
            request_id=request_id,
        )

    async def generate_product_selling_points(
            self,
            db: AsyncSession,
            *,
            request: ProductContentGenerateRequest,
            request_id: str | None = None,
    ) -> ContentGenerateResponse:
        product_context = await self._get_product_context(
            db,
            tenant_id=request.tenant_id,
            product_no=request.product_no,
        )

        state = ContentGenerationState(
            tenant_id=request.tenant_id,
            content_type="product_selling_points",
            biz_type="product",
            biz_id=request.product_no,
            variables=self._build_product_variables(
                content_type="product_selling_points",
                product_context=product_context,
                requirements=request.requirements,
                tone=request.tone,
                output_format="生成 3 到 5 条商品卖点，每条卖点简洁、具体、避免夸大承诺。",
            ),
        )

        return await self.generate_content_from_state(
            db,
            state=state,
            created_by=request.created_by,
            metadata_json=request.metadata_json,
            request_id=request_id,
        )

    async def generate_product_detail(
            self,
            db: AsyncSession,
            *,
            request: ProductContentGenerateRequest,
            request_id: str | None = None,
    ) -> ContentGenerateResponse:
        product_context = await self._get_product_context(
            db,
            tenant_id=request.tenant_id,
            product_no=request.product_no,
        )

        state = ContentGenerationState(
            tenant_id=request.tenant_id,
            content_type="product_detail",
            biz_type="product",
            biz_id=request.product_no,
            variables=self._build_product_variables(
                content_type="product_detail",
                product_context=product_context,
                requirements=request.requirements,
                tone=request.tone,
                output_format="生成详情页文案，包含主标题、核心卖点、使用场景、规格说明和注意事项。",
            ),
        )

        return await self.generate_content_from_state(
            db,
            state=state,
            created_by=request.created_by,
            metadata_json=request.metadata_json,
            request_id=request_id,
        )

    async def generate_campaign_copy(
            self,
            db: AsyncSession,
            *,
            request: CampaignContentGenerateRequest,
            request_id: str | None = None,
    ) -> ContentGenerateResponse:
        campaign_info = {
            "biz_type": "campaign",
            "content_type": "campaign_copy",
            "campaign_name": request.campaign_name,
            "campaign_context": request.campaign_context,
        }

        generation_requirement = (
                request.requirements
                or "生成活动文案，适合电商运营投放，避免虚假承诺和绝对化表达。"
        )

        state = ContentGenerationState(
            tenant_id=request.tenant_id,
            content_type="campaign_copy",
            biz_type="campaign",
            biz_id=request.campaign_name,
            variables={
                "scene": "content_generation",
                "content_type": "campaign_copy",
                "biz_type": "campaign",
                "campaign_name": request.campaign_name,
                "campaign_context": request.campaign_context,
                "product_info": "无指定商品。当前任务为活动文案生成，请主要参考 campaign_info 和 generation_requirement。",
                "campaign_info": json.dumps(
                    campaign_info,
                    ensure_ascii=False,
                    default=str,
                ),
                "requirements": request.requirements or "",
                "generation_requirement": generation_requirement,
                "tone": request.tone or "清晰、有转化感、合规",
                "output_format": "生成活动文案，适合电商运营投放，避免虚假承诺和绝对化表达。",
            },
        )

        return await self.generate_content_from_state(
            db,
            state=state,
            created_by=request.created_by,
            metadata_json=request.metadata_json,
            request_id=request_id,
        )

    async def generate_content_from_state(
            self,
            db: AsyncSession,
            *,
            state: ContentGenerationState,
            created_by: str | None = None,
            metadata_json: dict[str, Any] | None = None,
            request_id: str | None = None,
    ) -> ContentGenerateResponse:
        rendered_prompt_payload = await self._render_content_generation_prompt(
            db,
            tenant_id=state.tenant_id,
            variables=state.variables,
        )

        rendered_prompt = rendered_prompt_payload["rendered_content"]
        prompt_template_id = rendered_prompt_payload.get("template_id")
        prompt_version_id = rendered_prompt_payload.get("version_id")
        model_config = rendered_prompt_payload.get("model_config_json") or {}

        model_lookup_started_at = datetime.now(timezone.utc)

        model_response = await self._call_model_gateway(
            db,
            tenant_id=state.tenant_id,
            rendered_prompt=rendered_prompt,
            model_config=model_config,
            prompt_template_id=prompt_template_id,
            prompt_version_id=prompt_version_id,
            request_id=request_id,
        )

        generated_content = self._extract_model_content(model_response)
        model_response_summary = self._summarize_model_response(model_response)

        lookup_provider = (
                model_config.get("provider")
                or model_response_summary.get("provider")
        )
        lookup_model_name = (
                model_config.get("model")
                or model_config.get("model_name")
                or model_response_summary.get("model_name")
                or model_response_summary.get("model")
        )

        model_call_log_id = await self._find_recent_model_call_log_id(
            db,
            tenant_id=state.tenant_id,
            request_id=request_id,
            prompt_template_id=prompt_template_id,
            prompt_version_id=prompt_version_id,
            provider=lookup_provider,
            model_name=lookup_model_name,
            lookup_started_at=model_lookup_started_at,
        )

        if model_call_log_id is None:
            model_call_log_id = self._extract_model_call_log_id(model_response)

        brand = self._extract_brand_from_variables(state.variables)
        title = self._build_asset_title(
            content_type=state.content_type,
            variables=state.variables,
            generated_content=generated_content,
        )

        rule_check = self.review_service.run_rule_check(
            content=generated_content,
            brand=brand,
            content_type=state.content_type,
        )

        asset_group_id = uuid.uuid4()
        asset = ContentAsset(
            tenant_id=state.tenant_id,
            asset_group_id=asset_group_id,
            version=1,
            content_type=state.content_type,
            biz_type=state.biz_type,
            biz_id=state.biz_id,
            title=title,
            content=generated_content,
            status="draft",
            review_status=rule_check.review_status,
            source="llm_generated",
            prompt_template_id=prompt_template_id,
            prompt_version_id=prompt_version_id,
            model_call_log_id=model_call_log_id,
            generation_input_json=self._json_safe(
                {
                    "variables": state.variables,
                    "rendered_prompt_preview": rendered_prompt[:1000],
                }
            ),
            generation_output_json=self._json_safe(
                {
                    "content": generated_content,
                    "model_response_summary": model_response_summary,
                }
            ),
            rule_check_result_json=self._json_safe(rule_check.model_dump()),
            metadata_json=self._build_asset_metadata(
                model_call_log_id=model_call_log_id,
                extra_metadata=metadata_json,
            ),
            created_by=created_by,
        )

        asset = await self.asset_repository.create(db, asset)

        review = await self.review_service.create_rule_review_record(
            db,
            tenant_id=state.tenant_id,
            content_asset_id=asset.id,
            rule_check=rule_check,
            request_id=request_id,
            comments="内容生成后自动执行规则审核。",
        )

        await db.commit()
        await db.refresh(asset)
        await db.refresh(review)

        return ContentGenerateResponse(
            asset=asset,
            review=review,
            rule_check=rule_check,
        )

    async def submit_for_review(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            asset_id: UUID,
            operator_id: str | None = None,
            comments: str | None = None,
            request_id: str | None = None,
    ):
        asset = await self.asset_repository.get_by_id(
            db,
            tenant_id=tenant_id,
            asset_id=asset_id,
        )
        if asset is None:
            raise self._not_found("CONTENT_ASSET_NOT_FOUND", "内容资产不存在")

        if asset.status not in {"draft", "rejected"}:
            raise self._business_error(
                "CONTENT_ASSET_STATUS_INVALID",
                "只有 draft 或 rejected 状态的内容可以提交审核",
            )

        asset = await self.asset_repository.update_review_state(
            db,
            asset=asset,
            status="reviewing",
            review_status="manual_required",
        )

        review = await self._create_manual_review_record(
            db,
            tenant_id=tenant_id,
            content_asset_id=asset.id,
            review_status="manual_required",
            reviewer_id=operator_id,
            comments=comments or "提交人工审核。",
            request_id=request_id,
        )

        await db.commit()
        await db.refresh(asset)
        await db.refresh(review)
        return asset, review

    async def approve(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            asset_id: UUID,
            reviewer_id: str | None = None,
            comments: str | None = None,
            request_id: str | None = None,
    ):
        asset = await self.asset_repository.get_by_id(
            db,
            tenant_id=tenant_id,
            asset_id=asset_id,
        )
        if asset is None:
            raise self._not_found("CONTENT_ASSET_NOT_FOUND", "内容资产不存在")

        if asset.status != "reviewing":
            raise self._business_error(
                "CONTENT_ASSET_STATUS_INVALID",
                "只有 reviewing 状态的内容可以审批通过",
            )

        asset = await self.asset_repository.update_review_state(
            db,
            asset=asset,
            status="approved",
            review_status="passed",
            approved_by=reviewer_id,
            approved_at=datetime.now(timezone.utc),
        )

        review = await self._create_manual_review_record(
            db,
            tenant_id=tenant_id,
            content_asset_id=asset.id,
            review_status="passed",
            reviewer_id=reviewer_id,
            comments=comments or "人工审批通过。",
            request_id=request_id,
        )

        await db.commit()
        await db.refresh(asset)
        await db.refresh(review)
        return asset, review

    async def reject(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            asset_id: UUID,
            reviewer_id: str | None = None,
            comments: str | None = None,
            request_id: str | None = None,
    ):
        asset = await self.asset_repository.get_by_id(
            db,
            tenant_id=tenant_id,
            asset_id=asset_id,
        )
        if asset is None:
            raise self._not_found("CONTENT_ASSET_NOT_FOUND", "内容资产不存在")

        if asset.status != "reviewing":
            raise self._business_error(
                "CONTENT_ASSET_STATUS_INVALID",
                "只有 reviewing 状态的内容可以审批拒绝",
            )

        asset = await self.asset_repository.update_review_state(
            db,
            asset=asset,
            status="rejected",
            review_status="failed",
        )

        review = await self._create_manual_review_record(
            db,
            tenant_id=tenant_id,
            content_asset_id=asset.id,
            review_status="failed",
            reviewer_id=reviewer_id,
            comments=comments or "人工审批拒绝。",
            request_id=request_id,
        )

        await db.commit()
        await db.refresh(asset)
        await db.refresh(review)
        return asset, review

    async def get_asset(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            asset_id: UUID,
    ) -> ContentAsset:
        asset = await self.asset_repository.get_by_id(
            db,
            tenant_id=tenant_id,
            asset_id=asset_id,
        )
        if asset is None:
            raise self._not_found("CONTENT_ASSET_NOT_FOUND", "内容资产不存在")
        return asset

    async def list_versions(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            asset_group_id: UUID,
    ) -> list[ContentAsset]:
        return await self.asset_repository.list_versions(
            db,
            tenant_id=tenant_id,
            asset_group_id=asset_group_id,
        )

    async def _create_manual_review_record(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            content_asset_id: UUID,
            review_status: str,
            reviewer_id: str | None,
            comments: str | None,
            request_id: str | None,
    ):
        from app.models.content_review import ContentReview

        review = ContentReview(
            tenant_id=tenant_id,
            content_asset_id=content_asset_id,
            review_type="manual_review",
            review_status=review_status,
            reviewer_type="human",
            reviewer_id=reviewer_id,
            sensitive_check_result_json=None,
            brand_check_result_json=None,
            model_review_result_json=None,
            comments=comments,
            request_id=request_id,
        )
        return await self.review_repository.create(db, review)

    async def _get_product_context(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            product_no: str,
    ) -> dict[str, Any]:
        """通过 ProductService 获取商品上下文。

        这里做少量兼容，是为了不猜死窗口 3 ProductService 的具体方法名。
        仍然满足“不直接查库”的约束。
        """

        candidate_method_names = (
            "get_product_detail",
            "get_product_by_no",
            "get_product",
        )

        last_error: Exception | None = None

        for method_name in candidate_method_names:
            method = getattr(self.product_service, method_name, None)
            if method is None:
                continue

            try:
                product = await method(
                    db,
                    tenant_id=tenant_id,
                    product_no=product_no,
                )
                return self._to_plain_dict(product)
            except TypeError as exc:
                last_error = exc
                try:
                    product = await method(
                        db=db,
                        tenant_id=tenant_id,
                        product_no=product_no,
                    )
                    return self._to_plain_dict(product)
                except Exception as inner_exc:
                    last_error = inner_exc
            except Exception as exc:
                last_error = exc
                raise

        raise self._business_error(
            "PRODUCT_SERVICE_METHOD_NOT_FOUND",
            f"未找到可用的 ProductService 商品详情方法，最后错误：{last_error}",
        )

    def _build_product_variables(
            self,
            *,
            content_type: str,
            product_context: dict[str, Any],
            requirements: str | None,
            tone: str | None,
            output_format: str,
    ) -> dict[str, Any]:
        brand = self._deep_get(product_context, "brand")
        title = self._deep_get(product_context, "title")
        category = self._deep_get(product_context, "category")

        product_campaign_info = {
            "biz_type": "product",
            "content_type": content_type,
            "product_no": self._deep_get(product_context, "product_no"),
            "product_title": title,
            "brand": brand,
            "category": category,
            "product_info": product_context,
        }

        generation_requirement = requirements or output_format

        return {
            "scene": "content_generation",
            "content_type": content_type,
            "biz_type": "product",
            "product": product_context,
            "product_info": json.dumps(
                product_context,
                ensure_ascii=False,
                default=str,
            ),
            "product_no": self._deep_get(product_context, "product_no"),
            "product_title": title,
            "brand": brand,
            "category": category,
            "requirements": requirements or "",
            "generation_requirement": generation_requirement,
            "campaign_info": json.dumps(
                product_campaign_info,
                ensure_ascii=False,
                default=str,
            ),
            "tone": tone or "专业、清晰、有转化感、合规",
            "output_format": output_format,
            "compliance_rules": "避免绝对化表达、虚假承诺、医疗金融法律效果承诺、贬损竞品。",
        }

    async def _render_content_generation_prompt(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            variables: dict[str, Any],
    ) -> dict[str, Any]:
        """通过 PromptService 渲染 content_generation Prompt。"""

        payload = PromptRenderRequest(
            tenant_id=tenant_id,
            scene="content_generation",
            variables=variables,
        )

        result = await self.prompt_service.render_prompt(
            db,
            payload=payload,
        )

        return self._normalize_prompt_render_result(result)

    async def _call_model_gateway(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            rendered_prompt: str,
            model_config: dict[str, Any],
            prompt_template_id: UUID | None,
            prompt_version_id: UUID | None,
            request_id: str | None,
    ) -> Any:
        provider = model_config.get("provider")
        model = model_config.get("model")

        gateway = self.model_gateway or build_model_gateway(
            log_service=ModelCallLogService(db),
        )

        chat_request = ChatRequest(
            tenant_id=tenant_id,
            request_id=request_id,
            prompt_template_id=prompt_template_id,
            prompt_version_id=prompt_version_id,
            provider=provider,
            model=model,
            messages=[
                LLMMessage(
                    role="user",
                    content=rendered_prompt,
                )
            ],
            temperature=model_config.get("temperature", 0.7),
            max_tokens=model_config.get("max_tokens"),
            extra_body=model_config.get("extra_body"),
        )

        return await gateway.chat(chat_request)

    async def _find_recent_model_call_log_id(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            request_id: str | None,
            prompt_template_id: UUID | None,
            prompt_version_id: UUID | None,
            provider: str | None,
            model_name: str | None,
            lookup_started_at: datetime | None = None,
    ) -> UUID | None:
        """通过本次请求上下文反查最近一次模型调用日志。

        不修改 ModelGateway.chat() 返回结构。
        """

        if (
                not request_id
                or prompt_template_id is None
                or prompt_version_id is None
                or not provider
                or not model_name
        ):
            return None

        stmt = (
            select(ModelCallLog.id)
            .where(
                ModelCallLog.tenant_id == tenant_id,
                ModelCallLog.request_id == request_id,
                ModelCallLog.prompt_template_id == prompt_template_id,
                ModelCallLog.prompt_version_id == prompt_version_id,
                ModelCallLog.provider == provider,
                ModelCallLog.model_name == model_name,
                ModelCallLog.call_type == "chat",
            )
            .order_by(desc(ModelCallLog.created_at))
            .limit(1)
        )

        if lookup_started_at is not None:
            stmt = stmt.where(
                ModelCallLog.created_at >= lookup_started_at - timedelta(seconds=30)
            )

        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    def _build_asset_metadata(
            self,
            *,
            model_call_log_id: UUID | None,
            extra_metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        metadata = dict(extra_metadata or {})

        metadata["model_call_log_link_status"] = (
            "linked" if model_call_log_id is not None else "not_found"
        )

        return self._json_safe(metadata)

    def _normalize_prompt_render_result(self, result: Any) -> dict[str, Any]:
        data = self._to_plain_dict(result)

        rendered_content = (
                data.get("rendered_content")
                or data.get("content")
                or data.get("prompt")
                or data.get("text")
        )

        if not rendered_content:
            raise self._business_error(
                "PROMPT_RENDER_EMPTY",
                "Prompt 渲染结果为空",
            )

        return {
            "rendered_content": rendered_content,
            "template_id": data.get("template_id") or data.get("prompt_template_id"),
            "version_id": data.get("version_id") or data.get("prompt_version_id"),
            "template_key": data.get("template_key"),
            "scene": data.get("scene"),
            "version": data.get("version"),
            "variables": data.get("variables"),
            "model_config_json": data.get("model_config_json") or {},
            "gray_config_json": data.get("gray_config_json") or {},
        }

    def _extract_model_content(self, model_response: Any) -> str:
        data = self._to_plain_dict(model_response)

        content = (
                data.get("content")
                or data.get("text")
                or data.get("answer")
                or data.get("output")
        )

        if content is None and "choices" in data:
            try:
                content = data["choices"][0]["message"]["content"]
            except Exception:
                content = None

        if content is None and "data" in data:
            nested = data["data"]
            if isinstance(nested, dict):
                content = (
                        nested.get("content")
                        or nested.get("text")
                        or nested.get("answer")
                        or nested.get("output")
                )

        if not content:
            content = str(model_response)

        return str(content).strip()

    def _extract_model_call_log_id(self, model_response: Any) -> UUID | None:
        data = self._to_plain_dict(model_response)

        raw_id = (
                data.get("model_call_log_id")
                or data.get("log_id")
                or data.get("call_log_id")
        )

        if raw_id is None and isinstance(data.get("metadata_json"), dict):
            raw_id = data["metadata_json"].get("model_call_log_id")

        if not raw_id:
            return None

        try:
            return UUID(str(raw_id))
        except ValueError:
            return None

    def _extract_brand_from_variables(self, variables: dict[str, Any]) -> str | None:
        brand = variables.get("brand")
        if brand:
            return str(brand)

        product = variables.get("product") or variables.get("product_info")
        if isinstance(product, dict):
            brand = product.get("brand")
            if brand:
                return str(brand)

        return None

    def _build_asset_title(
            self,
            *,
            content_type: str,
            variables: dict[str, Any],
            generated_content: str,
    ) -> str:
        if content_type == "campaign_copy":
            campaign_name = variables.get("campaign_name")
            return f"{campaign_name or '活动'}文案"

        product_title = variables.get("product_title") or variables.get("product_no")
        content_type_name = {
            "product_title": "商品标题",
            "product_selling_points": "商品卖点",
            "product_detail": "详情页文案",
        }.get(content_type, content_type)

        if product_title:
            return f"{product_title} - {content_type_name}"

        return generated_content[:80]

    def _summarize_model_response(self, model_response: Any) -> dict[str, Any]:
        data = self._to_plain_dict(model_response)

        summary = {}
        for key in (
                "provider",
                "model_name",
                "model",
                "input_tokens",
                "output_tokens",
                "total_tokens",
                "latency_ms",
                "status",
                "model_call_log_id",
        ):
            if key in data:
                summary[key] = data[key]

        return summary

    def _to_plain_dict(self, value: Any) -> dict[str, Any]:
        if value is None:
            return {}

        if isinstance(value, dict):
            return value

        if hasattr(value, "model_dump"):
            return value.model_dump()

        if hasattr(value, "dict"):
            return value.dict()

        if hasattr(value, "__dict__"):
            return {
                key: item
                for key, item in vars(value).items()
                if not key.startswith("_")
            }

        return {"value": value}

    def _json_safe(self, value: Any) -> Any:
        return json.loads(
            json.dumps(
                value,
                ensure_ascii=False,
                default=str,
            )
        )

    def _deep_get(self, data: dict[str, Any], key: str) -> Any:
        if key in data:
            return data[key]

        for value in data.values():
            if isinstance(value, dict) and key in value:
                return value[key]

        return None

    def _business_error(self, code: str, message: str) -> BusinessException:
        try:
            return BusinessException(code=code, message=message)
        except TypeError:
            try:
                return BusinessException(message=message, code=code)
            except TypeError:
                return BusinessException(message)

    def _not_found(self, code: str, message: str) -> NotFoundException:
        try:
            return NotFoundException(code=code, message=message)
        except TypeError:
            try:
                return NotFoundException(message=message, code=code)
            except TypeError:
                return NotFoundException(message)
