from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_dependencies import CurrentUser, ensure_tenant_allowed, require_roles
from app.db.session import get_db_session
from app.schemas.content import (
    CampaignContentGenerateRequest,
    ContentManualReviewRequest,
    ContentReviewOnlyResponse,
    ContentReviewRequest,
    ContentSubmitReviewRequest,
    ContentVersionListResponse,
    ProductContentGenerateRequest,
)
from app.services.content_generation_service import ContentGenerationService
from app.services.content_review_service import ContentReviewService

router = APIRouter()


def get_content_generation_service() -> ContentGenerationService:
    return ContentGenerationService()


def get_content_review_service() -> ContentReviewService:
    return ContentReviewService()


def _get_request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def _to_jsonable(data: Any) -> Any:
    if data is None:
        return None

    if hasattr(data, "model_dump"):
        return data.model_dump(mode="json")

    if isinstance(data, list):
        return [_to_jsonable(item) for item in data]

    if isinstance(data, tuple):
        return [_to_jsonable(item) for item in data]

    if isinstance(data, dict):
        return {key: _to_jsonable(value) for key, value in data.items()}

    return data


def _success_response(
        *,
        request: Request,
        data: Any,
        message: str = "success",
) -> dict[str, Any]:
    return {
        "success": True,
        "code": "OK",
        "message": message,
        "data": _to_jsonable(data),
        "request_id": _get_request_id(request),
    }


@router.post("/generate/product-title")
async def generate_product_title(
        payload: ProductContentGenerateRequest,
        request: Request,
        db: AsyncSession = Depends(get_db_session),
):
    result = await get_content_generation_service().generate_product_title(
        db,
        request=payload,
        request_id=_get_request_id(request),
    )
    return _success_response(request=request, data=result)


@router.post("/generate/product-selling-points")
async def generate_product_selling_points(
        payload: ProductContentGenerateRequest,
        request: Request,
        db: AsyncSession = Depends(get_db_session),
):
    result = await get_content_generation_service().generate_product_selling_points(
        db,
        request=payload,
        request_id=_get_request_id(request),
    )
    return _success_response(request=request, data=result)


@router.post("/generate/product-detail")
async def generate_product_detail(
        payload: ProductContentGenerateRequest,
        request: Request,
        db: AsyncSession = Depends(get_db_session),
):
    result = await get_content_generation_service().generate_product_detail(
        db,
        request=payload,
        request_id=_get_request_id(request),
    )
    return _success_response(request=request, data=result)


@router.post("/generate/campaign-copy")
async def generate_campaign_copy(
        payload: CampaignContentGenerateRequest,
        request: Request,
        db: AsyncSession = Depends(get_db_session),
):
    result = await get_content_generation_service().generate_campaign_copy(
        db,
        request=payload,
        request_id=_get_request_id(request),
    )
    return _success_response(request=request, data=result)


@router.post("/review")
async def review_content(
        payload: ContentReviewRequest,
        request: Request,
):
    rule_check = get_content_review_service().run_rule_check(
        content=payload.content,
        brand=payload.brand,
        content_type=payload.content_type,
    )

    response = ContentReviewOnlyResponse(
        rule_check=rule_check,
        model_review_result_json=None,
    )

    return _success_response(request=request, data=response)


@router.get("/assets/{asset_id}")
async def get_content_asset(
        asset_id: UUID,
        tenant_id: UUID,
        request: Request,
        db: AsyncSession = Depends(get_db_session),
):
    asset = await get_content_generation_service().get_asset(
        db,
        tenant_id=tenant_id,
        asset_id=asset_id,
    )
    return _success_response(request=request, data=asset)


@router.get("/assets/{asset_group_id}/versions")
async def list_content_versions(
        asset_group_id: UUID,
        tenant_id: UUID,
        request: Request,
        db: AsyncSession = Depends(get_db_session),
):
    items = await get_content_generation_service().list_versions(
        db,
        tenant_id=tenant_id,
        asset_group_id=asset_group_id,
    )

    response = ContentVersionListResponse(
        asset_group_id=asset_group_id,
        items=items,
        total=len(items),
    )
    return _success_response(request=request, data=response)


@router.post("/assets/{asset_id}/submit-review")
async def submit_content_review(
        asset_id: UUID,
        payload: ContentSubmitReviewRequest,
        request: Request,
        db: AsyncSession = Depends(get_db_session),
        current_user: CurrentUser | None = Depends(require_roles("admin", "operator")),
):
    tenant_id = ensure_tenant_allowed(
        provided_tenant_id=payload.tenant_id,
        current_user=current_user,
    )

    operator_id = payload.operator_id
    if current_user is not None:
        operator_id = current_user.user_no

    asset, review = await get_content_generation_service().submit_for_review(
        db,
        tenant_id=tenant_id,
        asset_id=asset_id,
        operator_id=operator_id,
        comments=payload.comments,
        request_id=_get_request_id(request),
    )

    return _success_response(
        request=request,
        data={
            "asset": asset,
            "review": review,
        },
    )


@router.post("/assets/{asset_id}/approve")
async def approve_content_asset(
    asset_id: UUID,
    payload: ContentManualReviewRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    current_user: CurrentUser | None = Depends(require_roles("admin")),
):
    tenant_id = ensure_tenant_allowed(
        provided_tenant_id=payload.tenant_id,
        current_user=current_user,
    )

    reviewer_id = payload.reviewer_id
    if current_user is not None:
        reviewer_id = current_user.user_no

    asset, review = await get_content_generation_service().approve(
        db,
        tenant_id=tenant_id,
        asset_id=asset_id,
        reviewer_id=reviewer_id,
        comments=payload.comments,
        request_id=_get_request_id(request),
    )

    return _success_response(
        request=request,
        data={
            "asset": asset,
            "review": review,
        },
    )


@router.post("/assets/{asset_id}/reject")
async def reject_content_asset(
    asset_id: UUID,
    payload: ContentManualReviewRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    current_user: CurrentUser | None = Depends(require_roles("admin")),
):

    tenant_id = ensure_tenant_allowed(
        provided_tenant_id=payload.tenant_id,
        current_user=current_user,
    )

    reviewer_id = payload.reviewer_id
    if current_user is not None:
        reviewer_id = current_user.user_no

    asset, review = await get_content_generation_service().reject(
        db,
        tenant_id=tenant_id,
        asset_id=asset_id,
        reviewer_id=reviewer_id,
        comments=payload.comments,
        request_id=_get_request_id(request),
    )

    return _success_response(
        request=request,
        data={
            "asset": asset,
            "review": review,
        },
    )
