# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/05/01 11:12
IDE       :PyCharm
作者      :董宏升

Prompt 管理 API。

本文件只负责：
- 接收 HTTP 请求；
- 调用 PromptService；
- 返回统一 API 响应。

注意：
- 不写数据库查询；
- 不写复杂业务逻辑；
- 不调用模型网关；
- 不实现 Agent / RAG。

"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.helpers import get_request_id, to_response_data
from app.core.response import success_response
from app.db.session import get_db_session
from app.schemas.prompt import (
    PromptRenderRequest,
    PromptTemplateCreate,
    PromptTemplateStatus,
    PromptTemplateUpdate,
    PromptVersionCreate,
    PromptVersionStatus,
    PromptVersionUpdate,
)
from app.services.prompt_service import PromptService
from app.core.auth_dependencies import CurrentUser, ensure_tenant_allowed, require_roles

router = APIRouter()


@router.get("")
async def list_prompt_templates(
        request: Request,
        tenant_id: UUID = Query(..., description="租户 ID"),
        page: int = Query(default=1, ge=1, description="页码，从 1 开始"),
        page_size: int = Query(default=20, ge=1, le=100, description="每页数量"),
        scene: str | None = Query(default=None, description="Prompt 场景"),
        status_filter: PromptTemplateStatus | None = Query(
            default=None,
            alias="status",
            description="模板状态",
        ),
        keyword: str | None = Query(
            default=None,
            min_length=1,
            max_length=128,
            description="关键词，匹配 template_key / name / scene",
        ),
        db: AsyncSession = Depends(get_db_session),
):
    """
    分页查询 Prompt 模板。
    """

    service = PromptService()
    result = await service.list_templates(
        db,
        tenant_id=tenant_id,
        page=page,
        page_size=page_size,
        scene=scene,
        status_filter=status_filter,
        keyword=keyword,
    )

    return success_response(
        data=to_response_data(result),
        request_id=get_request_id(request),
    )


@router.post("")
async def create_prompt_template(
        payload: PromptTemplateCreate,
        request: Request,
        db: AsyncSession = Depends(get_db_session),
        current_user: CurrentUser | None = Depends(require_roles("admin")),
):
    """
    创建 Prompt 模板。
    """
    ensure_tenant_allowed(
        provided_tenant_id=getattr(payload, "tenant_id", None),
        current_user=current_user,
    )

    service = PromptService()
    result = await service.create_template(
        db,
        payload=payload,
    )

    return success_response(
        data=to_response_data(result),
        request_id=get_request_id(request),
    )


@router.post("/render")
async def render_prompt(
        payload: PromptRenderRequest,
        request: Request,
        db: AsyncSession = Depends(get_db_session),
):
    """
    渲染 Prompt。

    支持：
    - template_key + 当前启用版本；
    - template_key + 指定版本；
    - scene + 当前启用版本；
    - scene + 指定版本。
    """

    service = PromptService()
    result = await service.render_prompt(
        db,
        payload=payload,
    )

    return success_response(
        data=to_response_data(result),
        request_id=get_request_id(request),
    )


@router.get("/by-template-key/{template_key}/active")
async def get_active_prompt_by_template_key(
        template_key: str,
        request: Request,
        tenant_id: UUID = Query(..., description="租户 ID"),
        db: AsyncSession = Depends(get_db_session),
):
    """
    根据 template_key 获取当前启用 Prompt 版本。
    """

    service = PromptService()
    result = await service.get_active_version_by_template_key(
        db,
        tenant_id=tenant_id,
        template_key=template_key,
    )

    return success_response(
        data=to_response_data(result),
        request_id=get_request_id(request),
    )


@router.get("/by-scene/{scene}/active")
async def get_active_prompt_by_scene(
        scene: str,
        request: Request,
        tenant_id: UUID = Query(..., description="租户 ID"),
        db: AsyncSession = Depends(get_db_session),
):
    """
    根据 scene 获取当前启用 Prompt 版本。
    """

    service = PromptService()
    result = await service.get_active_version_by_scene(
        db,
        tenant_id=tenant_id,
        scene=scene,
    )

    return success_response(
        data=to_response_data(result),
        request_id=get_request_id(request),
    )


@router.post("/versions/{version_id}/activate")
async def activate_prompt_version(
        version_id: UUID,
        request: Request,
        tenant_id: UUID = Query(..., description="租户 ID"),
        db: AsyncSession = Depends(get_db_session),
        current_user: CurrentUser | None = Depends(require_roles("admin")),
):
    """
    查询 Prompt 版本详情。
    """
    tenant_id = ensure_tenant_allowed(
        provided_tenant_id=tenant_id,
        current_user=current_user,
    )

    service = PromptService()
    result = await service.get_version_detail(
        db,
        tenant_id=tenant_id,
        version_id=version_id,
    )

    return success_response(
        data=to_response_data(result),
        request_id=get_request_id(request),
    )


@router.post("/versions/{version_id}/activate")
async def activate_prompt_version(
        version_id: UUID,
        request: Request,
        tenant_id: UUID = Query(..., description="租户 ID"),
        db: AsyncSession = Depends(get_db_session),
):
    """
    启用 Prompt 版本。
    """

    service = PromptService()
    result = await service.activate_version(
        db,
        tenant_id=tenant_id,
        version_id=version_id,
    )

    return success_response(
        data=to_response_data(result),
        request_id=get_request_id(request),
    )


@router.post("/versions/{version_id}/deactivate")
async def deactivate_prompt_version(
        version_id: UUID,
        request: Request,
        tenant_id: UUID = Query(..., description="租户 ID"),
        db: AsyncSession = Depends(get_db_session),
        current_user: CurrentUser | None = Depends(require_roles("admin")),
):
    """
    停用 Prompt 版本。
    """

    service = PromptService()
    result = await service.deactivate_version(
        db,
        tenant_id=tenant_id,
        version_id=version_id,
    )

    return success_response(
        data=to_response_data(result),
        request_id=get_request_id(request),
    )


@router.get("/{template_id}")
async def get_prompt_template_detail(
        template_id: UUID,
        request: Request,
        tenant_id: UUID = Query(..., description="租户 ID"),
        db: AsyncSession = Depends(get_db_session),
):
    """
    查询 Prompt 模板详情，包含版本列表。
    """

    service = PromptService()
    result = await service.get_template_detail(
        db,
        tenant_id=tenant_id,
        template_id=template_id,
    )

    return success_response(
        data=to_response_data(result),
        request_id=get_request_id(request),
    )


@router.patch("/{template_id}")
async def update_prompt_template(
        template_id: UUID,
        payload: PromptTemplateUpdate,
        request: Request,
        db: AsyncSession = Depends(get_db_session),
        current_user: CurrentUser | None = Depends(require_roles("admin")),
):
    """
    更新 Prompt 模板。
    """
    ensure_tenant_allowed(
        provided_tenant_id=getattr(payload, "tenant_id", None),
        current_user=current_user,
    )

    service = PromptService()
    result = await service.update_template(
        db,
        template_id=template_id,
        payload=payload,
    )

    return success_response(
        data=to_response_data(result),
        request_id=get_request_id(request),
    )


@router.post("/{template_id}/deactivate")
async def deactivate_prompt_template(
        template_id: UUID,
        request: Request,
        tenant_id: UUID = Query(..., description="租户 ID"),
        db: AsyncSession = Depends(get_db_session),
        current_user: CurrentUser | None = Depends(require_roles("admin")),
):
    """
    停用 Prompt 模板。
    """
    tenant_id = ensure_tenant_allowed(
        provided_tenant_id=tenant_id,
        current_user=current_user,
    )

    service = PromptService()
    result = await service.deactivate_template(
        db,
        tenant_id=tenant_id,
        template_id=template_id,
    )

    return success_response(
        data=to_response_data(result),
        request_id=get_request_id(request),
    )


@router.delete("/{template_id}")
async def archive_prompt_template(
        template_id: UUID,
        request: Request,
        tenant_id: UUID = Query(..., description="租户 ID"),
        db: AsyncSession = Depends(get_db_session),
        current_user: CurrentUser | None = Depends(require_roles("admin")),
):
    """
    归档 Prompt 模板。

    注意：
    - 使用软删除；
    - 不物理删除数据库记录。
    """
    tenant_id = ensure_tenant_allowed(
        provided_tenant_id=tenant_id,
        current_user=current_user,
    )

    service = PromptService()
    result = await service.archive_template(
        db,
        tenant_id=tenant_id,
        template_id=template_id,
    )

    return success_response(
        data=to_response_data(result),
        request_id=get_request_id(request),
    )


@router.get("/{template_id}/versions")
async def list_prompt_versions(
        template_id: UUID,
        request: Request,
        tenant_id: UUID = Query(..., description="租户 ID"),
        page: int = Query(default=1, ge=1, description="页码，从 1 开始"),
        page_size: int = Query(default=20, ge=1, le=100, description="每页数量"),
        status_filter: PromptVersionStatus | None = Query(
            default=None,
            alias="status",
            description="版本状态",
        ),
        db: AsyncSession = Depends(get_db_session),
):
    """
    分页查询某个模板下的 Prompt 版本。
    """

    service = PromptService()
    result = await service.list_versions(
        db,
        tenant_id=tenant_id,
        template_id=template_id,
        page=page,
        page_size=page_size,
        status_filter=status_filter,
    )

    return success_response(
        data=to_response_data(result),
        request_id=get_request_id(request),
    )


@router.post("/{template_id}/versions")
async def create_prompt_version(
        template_id: UUID,
        payload: PromptVersionCreate,
        request: Request,
        db: AsyncSession = Depends(get_db_session),
        current_user: CurrentUser | None = Depends(require_roles("admin")),
):
    """
    创建 Prompt 版本。
    """
    ensure_tenant_allowed(
        provided_tenant_id=getattr(payload, "tenant_id", None),
        current_user=current_user,
    )

    service = PromptService()
    result = await service.create_version(
        db,
        template_id=template_id,
        payload=payload,
    )

    return success_response(
        data=to_response_data(result),
        request_id=get_request_id(request),
    )
