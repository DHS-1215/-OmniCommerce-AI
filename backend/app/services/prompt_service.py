# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/05/01 10:34
IDE       :PyCharm
作者      :董宏升

Prompt 管理业务服务层。

本文件负责：
- Prompt 模板 CRUD；
- Prompt 版本管理；
- 启用 / 停用；
- 按 template_key / scene 获取当前启用版本；
- Prompt 变量渲染；
- 事务提交 / 回滚；
- 业务异常归一化。

注意：
- 不直接调用外部模型 API；
- 不实现 Agent；
- 不实现 RAG；
- 不把 Prompt 硬编码到业务代码。
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.core.exceptions import BaseAppException
from app.prompts.renderer import PromptRenderer
from app.repositories.prompt_repository import PromptRepository
from app.schemas.common import PageResponse
from app.schemas.prompt import (
    PromptActiveVersionResponse,
    PromptRenderRequest,
    PromptRenderResponse,
    PromptTemplateCreate,
    PromptTemplateDetailResponse,
    PromptTemplateResponse,
    PromptTemplateUpdate,
    PromptVersionCreate,
    PromptVersionResponse,
    PromptVersionUpdate,
)


class PromptService:
    """
    Prompt 管理业务服务。

    关键业务规则：
    - 同一租户下 template_key 唯一；
    - 模板默认按 active / inactive / archived 管理；
    - 同一模板下版本号从 1 开始递增；
    - 同一模板同一时间只能有一个 is_active=true 且 status=active 的版本；
    - 渲染 Prompt 时必须能追踪 template_id / version_id；
    - Prompt 模块不直接调用模型网关。
    """

    def __init__(self) -> None:
        self.prompt_repository = PromptRepository()
        self.prompt_renderer = PromptRenderer()

    async def list_templates(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            page: int,
            page_size: int,
            scene: str | None = None,
            status_filter: str | None = None,
            keyword: str | None = None,
    ) -> PageResponse[PromptTemplateResponse]:
        """
        分页查询 Prompt 模板。
        """

        templates, total = await self.prompt_repository.list_templates(
            db,
            tenant_id=tenant_id,
            page=page,
            page_size=page_size,
            scene=scene,
            status=status_filter,
            keyword=keyword,
        )

        return PageResponse[PromptTemplateResponse](
            items=[PromptTemplateResponse.model_validate(item) for item in templates],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def create_template(
            self,
            db: AsyncSession,
            *,
            payload: PromptTemplateCreate,
    ) -> PromptTemplateResponse:
        """
        创建 Prompt 模板。
        """

        exists_template = await self.prompt_repository.get_template_by_key(
            db,
            tenant_id=payload.tenant_id,
            template_key=payload.template_key,
            status=None,
        )
        if exists_template is not None:
            raise BaseAppException(
                code="PROMPT_TEMPLATE_KEY_CONFLICT",
                message="Prompt 模板 Key 已存在",
                status_code=status.HTTP_409_CONFLICT,
                data={"template_key": payload.template_key},
            )

        try:
            template = await self.prompt_repository.create_template(
                db,
                tenant_id=payload.tenant_id,
                template_key=payload.template_key,
                name=payload.name,
                scene=payload.scene,
                description=payload.description,
                metadata_json=payload.metadata_json,
                status="active",
            )

            await db.commit()
            await db.refresh(template)
        except IntegrityError as exc:
            await db.rollback()
            raise BaseAppException(
                code="PROMPT_TEMPLATE_KEY_CONFLICT",
                message="Prompt 模板 Key 已存在",
                status_code=status.HTTP_409_CONFLICT,
                data={"template_key": payload.template_key},
            ) from exc
        except Exception:
            await db.rollback()
            raise

        return PromptTemplateResponse.model_validate(template)

    async def get_template_detail(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            template_id: UUID,
    ) -> PromptTemplateDetailResponse:
        """
        查询 Prompt 模板详情，包含版本列表。
        """

        template = await self.prompt_repository.get_template_by_id(
            db,
            tenant_id=tenant_id,
            template_id=template_id,
            status=None,
            include_versions=True,
        )
        if template is None:
            raise BaseAppException(
                code="PROMPT_TEMPLATE_NOT_FOUND",
                message="Prompt 模板不存在",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        data = PromptTemplateDetailResponse.model_validate(template)
        versions = [
            version
            for version in template.versions
            if version.deleted_at is None
        ]
        versions.sort(key=lambda item: item.version, reverse=True)
        data.versions = [
            PromptVersionResponse.model_validate(version)
            for version in versions
        ]
        return data

    async def update_template(
            self,
            db: AsyncSession,
            *,
            template_id: UUID,
            payload: PromptTemplateUpdate,
    ) -> PromptTemplateResponse:
        """
        更新 Prompt 模板。
        """

        template = await self.prompt_repository.get_template_by_id(
            db,
            tenant_id=payload.tenant_id,
            template_id=template_id,
            status=None,
        )
        if template is None:
            raise BaseAppException(
                code="PROMPT_TEMPLATE_NOT_FOUND",
                message="Prompt 模板不存在",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        values = payload.model_dump(
            exclude={"tenant_id"},
            exclude_unset=True,
        )
        if not values:
            return PromptTemplateResponse.model_validate(template)

        try:
            template = await self.prompt_repository.update_template(
                template=template,
                values=values,
            )
            await db.commit()
            await db.refresh(template)
        except Exception:
            await db.rollback()
            raise

        return PromptTemplateResponse.model_validate(template)

    async def deactivate_template(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            template_id: UUID,
    ) -> PromptTemplateResponse:
        """
        停用 Prompt 模板。

        说明：
        - 这里不是软删除；
        - 停用后 status=inactive；
        - 历史版本仍保留；
        - 后续按 scene / template_key 获取 active Prompt 时不会命中。
        """

        template = await self.prompt_repository.get_template_by_id(
            db,
            tenant_id=tenant_id,
            template_id=template_id,
            status=None,
        )
        if template is None:
            raise BaseAppException(
                code="PROMPT_TEMPLATE_NOT_FOUND",
                message="Prompt 模板不存在",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        try:
            template.status = "inactive"
            await self.prompt_repository.deactivate_versions_by_template_id(
                db,
                tenant_id=tenant_id,
                template_id=template_id,
            )

            await db.commit()
            await db.refresh(template)
        except Exception:
            await db.rollback()
            raise

        return PromptTemplateResponse.model_validate(template)

    async def archive_template(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            template_id: UUID,
    ) -> PromptTemplateResponse:
        """
        归档 Prompt 模板。

        说明：
        - 归档使用软删除 deleted_at；
        - status 设置为 archived；
        - 当前版本全部停用；
        - 用于后台删除语义。
        """

        template = await self.prompt_repository.get_template_by_id(
            db,
            tenant_id=tenant_id,
            template_id=template_id,
            status=None,
        )
        if template is None:
            raise BaseAppException(
                code="PROMPT_TEMPLATE_NOT_FOUND",
                message="Prompt 模板不存在",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        try:
            await self.prompt_repository.soft_delete_template(template=template)
            await self.prompt_repository.deactivate_versions_by_template_id(
                db,
                tenant_id=tenant_id,
                template_id=template_id,
            )

            await db.commit()
            await db.refresh(template)
        except Exception:
            await db.rollback()
            raise

        return PromptTemplateResponse.model_validate(template)

    async def list_versions(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            template_id: UUID,
            page: int,
            page_size: int,
            status_filter: str | None = None,
    ) -> PageResponse[PromptVersionResponse]:
        """
        分页查询 Prompt 版本。
        """

        template = await self.prompt_repository.get_template_by_id(
            db,
            tenant_id=tenant_id,
            template_id=template_id,
            status=None,
        )
        if template is None:
            raise BaseAppException(
                code="PROMPT_TEMPLATE_NOT_FOUND",
                message="Prompt 模板不存在",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        versions, total = await self.prompt_repository.list_versions(
            db,
            tenant_id=tenant_id,
            template_id=template_id,
            page=page,
            page_size=page_size,
            status=status_filter,
        )

        return PageResponse[PromptVersionResponse](
            items=[PromptVersionResponse.model_validate(item) for item in versions],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def get_version_detail(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            version_id: UUID,
    ) -> PromptVersionResponse:
        """
        查询 Prompt 版本详情。
        """

        prompt_version = await self.prompt_repository.get_version_by_id(
            db,
            tenant_id=tenant_id,
            version_id=version_id,
            status=None,
        )
        if prompt_version is None:
            raise BaseAppException(
                code="PROMPT_VERSION_NOT_FOUND",
                message="Prompt 版本不存在",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        return PromptVersionResponse.model_validate(prompt_version)

    async def create_version(
            self,
            db: AsyncSession,
            *,
            template_id: UUID,
            payload: PromptVersionCreate,
    ) -> PromptVersionResponse:
        """
        创建 Prompt 版本。

        如果 payload.is_active=true：
        - 先停用该模板下其他启用版本；
        - 当前新版本 status=active；
        - 当前新版本 is_active=true。
        """

        template = await self.prompt_repository.get_template_by_id(
            db,
            tenant_id=payload.tenant_id,
            template_id=template_id,
            status=None,
        )
        if template is None:
            raise BaseAppException(
                code="PROMPT_TEMPLATE_NOT_FOUND",
                message="Prompt 模板不存在",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        if template.status != "active":
            raise BaseAppException(
                code="PROMPT_TEMPLATE_INACTIVE",
                message="Prompt 模板不是 active 状态，不能创建启用版本",
                status_code=status.HTTP_400_BAD_REQUEST,
                data={"template_id": str(template_id), "status": template.status},
            )

        next_version = await self.prompt_repository.get_next_version_number(
            db,
            tenant_id=payload.tenant_id,
            template_id=template_id,
        )

        try:
            if payload.is_active:
                await self.prompt_repository.deactivate_versions_by_template_id(
                    db,
                    tenant_id=payload.tenant_id,
                    template_id=template_id,
                )

            prompt_version = await self.prompt_repository.create_version(
                db,
                tenant_id=payload.tenant_id,
                template_id=template_id,
                version=next_version,
                content=payload.content,
                variable_schema_json=payload.variable_schema_json,
                model_config_json=payload.model_config_json,
                gray_config_json=payload.gray_config_json,
                is_active=payload.is_active,
                status="active" if payload.is_active else "draft",
                change_log=payload.change_log,
            )

            await db.commit()
            await db.refresh(prompt_version)
        except IntegrityError as exc:
            await db.rollback()
            raise BaseAppException(
                code="PROMPT_VERSION_CONFLICT",
                message="Prompt 版本号冲突",
                status_code=status.HTTP_409_CONFLICT,
                data={"template_id": str(template_id), "version": next_version},
            ) from exc
        except Exception:
            await db.rollback()
            raise

        return PromptVersionResponse.model_validate(prompt_version)

    async def update_version(
            self,
            db: AsyncSession,
            *,
            version_id: UUID,
            payload: PromptVersionUpdate,
    ) -> PromptVersionResponse:
        """
        更新 Prompt 版本。

        注意：
        - 不允许通过更新接口直接激活版本；
        - 激活版本必须走 activate_version；
        - 这样可以保证同模板只有一个 active 版本。
        """

        prompt_version = await self.prompt_repository.get_version_by_id(
            db,
            tenant_id=payload.tenant_id,
            version_id=version_id,
            status=None,
        )
        if prompt_version is None:
            raise BaseAppException(
                code="PROMPT_VERSION_NOT_FOUND",
                message="Prompt 版本不存在",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        values = payload.model_dump(
            exclude={"tenant_id"},
            exclude_unset=True,
        )
        if not values:
            return PromptVersionResponse.model_validate(prompt_version)

        if values.get("status") == "active":
            raise BaseAppException(
                code="PROMPT_VERSION_ACTIVATE_REQUIRED",
                message="不能通过更新接口直接激活版本，请使用启用版本接口",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        if "status" in values and values["status"] in {"inactive", "archived", "draft"}:
            values["is_active"] = False

        try:
            prompt_version = await self.prompt_repository.update_version(
                prompt_version=prompt_version,
                values=values,
            )
            await db.commit()
            await db.refresh(prompt_version)
        except Exception:
            await db.rollback()
            raise

        return PromptVersionResponse.model_validate(prompt_version)

    async def activate_version(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            version_id: UUID,
    ) -> PromptVersionResponse:
        """
        启用指定 Prompt 版本。

        核心规则：
        - 同一个模板下只能有一个 is_active=true 的版本；
        - 启用目标版本前，先停用同模板其他版本。
        """

        prompt_version = await self.prompt_repository.get_version_by_id(
            db,
            tenant_id=tenant_id,
            version_id=version_id,
            status=None,
        )
        if prompt_version is None:
            raise BaseAppException(
                code="PROMPT_VERSION_NOT_FOUND",
                message="Prompt 版本不存在",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        template = await self.prompt_repository.get_template_by_id(
            db,
            tenant_id=tenant_id,
            template_id=prompt_version.template_id,
            status=None,
        )
        if template is None:
            raise BaseAppException(
                code="PROMPT_TEMPLATE_NOT_FOUND",
                message="Prompt 模板不存在",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        if template.status != "active":
            raise BaseAppException(
                code="PROMPT_TEMPLATE_INACTIVE",
                message="Prompt 模板不是 active 状态，不能启用版本",
                status_code=status.HTTP_400_BAD_REQUEST,
                data={"template_id": str(template.id), "status": template.status},
            )

        try:
            await self.prompt_repository.deactivate_versions_by_template_id(
                db,
                tenant_id=tenant_id,
                template_id=prompt_version.template_id,
            )
            prompt_version = await self.prompt_repository.activate_version(
                prompt_version=prompt_version,
            )

            await db.commit()
            await db.refresh(prompt_version)
        except Exception:
            await db.rollback()
            raise

        return PromptVersionResponse.model_validate(prompt_version)

    async def deactivate_version(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            version_id: UUID,
    ) -> PromptVersionResponse:
        """
        停用指定 Prompt 版本。
        """

        prompt_version = await self.prompt_repository.get_version_by_id(
            db,
            tenant_id=tenant_id,
            version_id=version_id,
            status=None,
        )
        if prompt_version is None:
            raise BaseAppException(
                code="PROMPT_VERSION_NOT_FOUND",
                message="Prompt 版本不存在",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        try:
            prompt_version = await self.prompt_repository.deactivate_version(
                prompt_version=prompt_version,
            )
            await db.commit()
            await db.refresh(prompt_version)
        except Exception:
            await db.rollback()
            raise

        return PromptVersionResponse.model_validate(prompt_version)

    async def get_active_version_by_template_key(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            template_key: str,
    ) -> PromptActiveVersionResponse:
        """
        根据 template_key 获取当前启用 Prompt 版本。
        """

        row = await self.prompt_repository.get_active_version_by_template_key(
            db,
            tenant_id=tenant_id,
            template_key=template_key,
        )
        if row is None:
            raise BaseAppException(
                code="PROMPT_ACTIVE_VERSION_NOT_FOUND",
                message="未找到当前启用的 Prompt 版本",
                status_code=status.HTTP_404_NOT_FOUND,
                data={"template_key": template_key},
            )

        template, prompt_version = row

        return PromptActiveVersionResponse(
            template=PromptTemplateResponse.model_validate(template),
            version=PromptVersionResponse.model_validate(prompt_version),
        )

    async def get_active_version_by_scene(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            scene: str,
    ) -> PromptActiveVersionResponse:
        """
        根据 scene 获取当前启用 Prompt 版本。
        """

        row = await self.prompt_repository.get_active_version_by_scene(
            db,
            tenant_id=tenant_id,
            scene=scene,
        )
        if row is None:
            raise BaseAppException(
                code="PROMPT_ACTIVE_VERSION_NOT_FOUND",
                message="未找到当前启用的 Prompt 版本",
                status_code=status.HTTP_404_NOT_FOUND,
                data={"scene": scene},
            )

        template, prompt_version = row

        return PromptActiveVersionResponse(
            template=PromptTemplateResponse.model_validate(template),
            version=PromptVersionResponse.model_validate(prompt_version),
        )

    async def render_prompt(
            self,
            db: AsyncSession,
            *,
            payload: PromptRenderRequest,
    ) -> PromptRenderResponse:
        """
        渲染 Prompt。

        支持：
        - template_key + 当前启用版本；
        - template_key + 指定版本；
        - scene + 当前启用版本；
        - scene + 指定版本不建议使用，因为 scene 不是唯一键；
          如果传了 version 且只传 scene，当前实现仍先取 scene 下最新 active 模板，再查该模板版本。
        """

        template = None
        prompt_version = None

        if payload.template_key:
            template = await self.prompt_repository.get_template_by_key(
                db,
                tenant_id=payload.tenant_id,
                template_key=payload.template_key,
                status="active",
            )
            if template is None:
                raise BaseAppException(
                    code="PROMPT_TEMPLATE_NOT_FOUND",
                    message="Prompt 模板不存在或未启用",
                    status_code=status.HTTP_404_NOT_FOUND,
                    data={"template_key": payload.template_key},
                )

            if payload.version is not None:
                prompt_version = await self.prompt_repository.get_version_by_number(
                    db,
                    tenant_id=payload.tenant_id,
                    template_id=template.id,
                    version=payload.version,
                    status=None,
                )
            else:
                prompt_version = await self.prompt_repository.get_active_version_by_template_id(
                    db,
                    tenant_id=payload.tenant_id,
                    template_id=template.id,
                )

        elif payload.scene:
            row = await self.prompt_repository.get_active_version_by_scene(
                db,
                tenant_id=payload.tenant_id,
                scene=payload.scene,
            )
            if row is None:
                raise BaseAppException(
                    code="PROMPT_ACTIVE_VERSION_NOT_FOUND",
                    message="未找到当前启用的 Prompt 版本",
                    status_code=status.HTTP_404_NOT_FOUND,
                    data={"scene": payload.scene},
                )

            template, active_version = row

            if payload.version is not None:
                prompt_version = await self.prompt_repository.get_version_by_number(
                    db,
                    tenant_id=payload.tenant_id,
                    template_id=template.id,
                    version=payload.version,
                    status=None,
                )
            else:
                prompt_version = active_version

        if template is None:
            raise BaseAppException(
                code="PROMPT_RENDER_TARGET_REQUIRED",
                message="template_key 和 scene 至少需要传一个",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        if prompt_version is None:
            raise BaseAppException(
                code="PROMPT_VERSION_NOT_FOUND",
                message="Prompt 版本不存在",
                status_code=status.HTTP_404_NOT_FOUND,
                data={
                    "template_key": template.template_key,
                    "scene": template.scene,
                    "version": payload.version,
                },
            )

        if prompt_version.status != "active" and payload.version is None:
            raise BaseAppException(
                code="PROMPT_ACTIVE_VERSION_NOT_FOUND",
                message="未找到当前启用的 Prompt 版本",
                status_code=status.HTTP_404_NOT_FOUND,
                data={"template_key": template.template_key},
            )

        if payload.version is None and not prompt_version.is_active:
            raise BaseAppException(
                code="PROMPT_ACTIVE_VERSION_NOT_FOUND",
                message="未找到当前启用的 Prompt 版本",
                status_code=status.HTTP_404_NOT_FOUND,
                data={"template_key": template.template_key},
            )

        rendered_content = self.prompt_renderer.render(
            content=prompt_version.content,
            variables=payload.variables,
            variable_schema_json=prompt_version.variable_schema_json,
        )

        return PromptRenderResponse(
            template_id=template.id,
            version_id=prompt_version.id,
            template_key=template.template_key,
            scene=template.scene,
            version=prompt_version.version,
            rendered_content=rendered_content,
            variables=payload.variables,
            model_config_json=prompt_version.model_config_json,
            gray_config_json=prompt_version.gray_config_json,
        )
