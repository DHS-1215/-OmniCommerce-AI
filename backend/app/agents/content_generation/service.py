from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.content_generation.state import ContentGenerationState


class ContentGenerationWorkflowService:
    """内容生成轻量受控编排。

    本类只做流程包装，不做自由 Agent，不做自主工具规划。
    真实业务逻辑仍由 ContentGenerationService 负责。
    """

    async def run(
        self,
        db: AsyncSession,
        *,
        state: ContentGenerationState,
        generation_service,
        request_id: str | None = None,
    ) -> ContentGenerationState:
        try:
            state.status = "running"

            result = await generation_service.generate_content_from_state(
                db,
                state=state,
                request_id=request_id,
            )

            state.content_asset_id = result.asset.id
            state.rule_check_result = result.rule_check.model_dump()
            if result.review:
                state.content_review_id = result.review.id

            state.generated_content = result.asset.content
            state.title = result.asset.title
            state.prompt_template_id = result.asset.prompt_template_id
            state.prompt_version_id = result.asset.prompt_version_id
            state.model_call_log_id = result.asset.model_call_log_id
            state.status = "completed"
            return state

        except Exception as exc:
            state.status = "failed"
            state.error_message = str(exc)
            raise
