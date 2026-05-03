# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/05/01 09:18
IDE       :PyCharm
作者      :董宏升

Prompt 模板与版本数据访问层。

本文件只负责：
- PromptTemplate 查询 / 创建 / 更新 / 软删除；
- PromptVersion 查询 / 创建 / 更新 / 启停状态更新；
- 按 scene / template_key 查当前启用版本。

注意：
- 不做业务异常抛出；
- 不做变量渲染；
- 不调用模型网关；
- 不实现 Agent / RAG。
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.prompt import PromptTemplate, PromptVersion


class PromptRepository:
    """
    Prompt 模板与版本数据访问层。
    """

    async def list_templates(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            page: int,
            page_size: int,
            scene: str | None = None,
            status: str | None = None,
            keyword: str | None = None,
    ) -> tuple[list[PromptTemplate], int]:
        """
        分页查询 Prompt 模板。
        """

        conditions = [
            PromptTemplate.tenant_id == tenant_id,
            PromptTemplate.deleted_at.is_(None),
        ]

        if scene:
            conditions.append(PromptTemplate.scene == scene)

        if status:
            conditions.append(PromptTemplate.status == status)

        if keyword:
            like_keyword = f"%{keyword}%"
            conditions.append(
                or_(
                    PromptTemplate.template_key.ilike(like_keyword),
                    PromptTemplate.name.ilike(like_keyword),
                    PromptTemplate.scene.ilike(like_keyword),
                )
            )

        count_stmt = select(func.count()).select_from(PromptTemplate).where(*conditions)
        total = await db.scalar(count_stmt)
        total = int(total or 0)

        stmt = (
            select(PromptTemplate)
            .where(*conditions)
            .order_by(PromptTemplate.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all()), total

    async def get_template_by_id(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            template_id: UUID,
            status: str | None = None,
            include_versions: bool = False,
    ) -> PromptTemplate | None:
        """
        根据模板 ID 查询 Prompt 模板。
        """

        conditions = [
            PromptTemplate.tenant_id == tenant_id,
            PromptTemplate.id == template_id,
            PromptTemplate.deleted_at.is_(None),
        ]

        if status:
            conditions.append(PromptTemplate.status == status)

        stmt = select(PromptTemplate).where(*conditions)

        if include_versions:
            stmt = stmt.options(selectinload(PromptTemplate.versions))

        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_template_by_key(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            template_key: str,
            status: str | None = None,
            include_versions: bool = False,
    ) -> PromptTemplate | None:
        """
        根据 template_key 查询 Prompt 模板。
        """

        conditions = [
            PromptTemplate.tenant_id == tenant_id,
            PromptTemplate.template_key == template_key,
            PromptTemplate.deleted_at.is_(None),
        ]

        if status:
            conditions.append(PromptTemplate.status == status)

        stmt = select(PromptTemplate).where(*conditions)

        if include_versions:
            stmt = stmt.options(selectinload(PromptTemplate.versions))

        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_template(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            template_key: str,
            name: str,
            scene: str,
            description: str | None = None,
            metadata_json: dict[str, Any] | None = None,
            status: str = "active",
    ) -> PromptTemplate:
        """
        创建 Prompt 模板。

        注意：
        - 这里只 add，不 commit；
        - commit 由 service 层统一处理。
        """

        template = PromptTemplate(
            tenant_id=tenant_id,
            template_key=template_key,
            name=name,
            scene=scene,
            description=description,
            metadata_json=metadata_json,
            status=status,
        )
        db.add(template)
        return template

    async def update_template(
            self,
            *,
            template: PromptTemplate,
            values: dict[str, Any],
    ) -> PromptTemplate:
        """
        更新 Prompt 模板对象。

        注意：
        - 这里只修改 ORM 对象；
        - commit 由 service 层统一处理。
        """

        for field_name, value in values.items():
            if hasattr(template, field_name):
                setattr(template, field_name, value)

        return template

    async def soft_delete_template(
            self,
            *,
            template: PromptTemplate,
    ) -> PromptTemplate:
        """
        软删除 Prompt 模板。
        """

        template.deleted_at = datetime.utcnow()
        template.status = "archived"
        return template

    async def list_versions(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            template_id: UUID,
            page: int,
            page_size: int,
            status: str | None = None,
    ) -> tuple[list[PromptVersion], int]:
        """
        分页查询某个模板下的版本列表。
        """

        conditions = [
            PromptVersion.tenant_id == tenant_id,
            PromptVersion.template_id == template_id,
            PromptVersion.deleted_at.is_(None),
        ]

        if status:
            conditions.append(PromptVersion.status == status)

        count_stmt = select(func.count()).select_from(PromptVersion).where(*conditions)
        total = await db.scalar(count_stmt)
        total = int(total or 0)

        stmt = (
            select(PromptVersion)
            .where(*conditions)
            .order_by(PromptVersion.version.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all()), total

    async def get_version_by_id(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            version_id: UUID,
            status: str | None = None,
    ) -> PromptVersion | None:
        """
        根据版本 ID 查询 Prompt 版本。
        """

        conditions = [
            PromptVersion.tenant_id == tenant_id,
            PromptVersion.id == version_id,
            PromptVersion.deleted_at.is_(None),
        ]

        if status:
            conditions.append(PromptVersion.status == status)

        stmt = select(PromptVersion).where(*conditions)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_version_by_number(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            template_id: UUID,
            version: int,
            status: str | None = None,
    ) -> PromptVersion | None:
        """
        根据模板 ID + 版本号查询 Prompt 版本。
        """

        conditions = [
            PromptVersion.tenant_id == tenant_id,
            PromptVersion.template_id == template_id,
            PromptVersion.version == version,
            PromptVersion.deleted_at.is_(None),
        ]

        if status:
            conditions.append(PromptVersion.status == status)

        stmt = select(PromptVersion).where(*conditions)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_next_version_number(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            template_id: UUID,
    ) -> int:
        """
        获取下一个版本号。

        当前规则：
        - 同一模板下 version 从 1 开始递增；
        - 不复用已归档 / 软删除版本号。
        """

        stmt = select(func.max(PromptVersion.version)).where(
            PromptVersion.tenant_id == tenant_id,
            PromptVersion.template_id == template_id,
        )
        max_version = await db.scalar(stmt)
        return int(max_version or 0) + 1

    async def create_version(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            template_id: UUID,
            version: int,
            content: str,
            variable_schema_json: dict[str, Any] | None = None,
            model_config_json: dict[str, Any] | None = None,
            gray_config_json: dict[str, Any] | None = None,
            is_active: bool = False,
            status: str = "draft",
            change_log: str | None = None,
    ) -> PromptVersion:
        """
        创建 Prompt 版本。

        注意：
        - 这里只 add，不 commit；
        - commit 由 service 层统一处理。
        """

        prompt_version = PromptVersion(
            tenant_id=tenant_id,
            template_id=template_id,
            version=version,
            content=content,
            variable_schema_json=variable_schema_json,
            model_config_json=model_config_json,
            gray_config_json=gray_config_json,
            is_active=is_active,
            status=status,
            change_log=change_log,
        )
        db.add(prompt_version)
        return prompt_version

    async def update_version(
            self,
            *,
            prompt_version: PromptVersion,
            values: dict[str, Any],
    ) -> PromptVersion:
        """
        更新 Prompt 版本对象。
        """

        for field_name, value in values.items():
            if hasattr(prompt_version, field_name):
                setattr(prompt_version, field_name, value)

        return prompt_version

    async def deactivate_versions_by_template_id(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            template_id: UUID,
    ) -> None:
        """
        停用某个模板下所有当前启用版本。

        业务含义：
        - 同一个模板同一时间只能有一个 is_active=true 的版本；
        - 激活新版本前，应先调用该方法停用旧版本。
        """

        stmt = (
            update(PromptVersion)
            .where(
                PromptVersion.tenant_id == tenant_id,
                PromptVersion.template_id == template_id,
                PromptVersion.deleted_at.is_(None),
                PromptVersion.is_active.is_(True),
            )
            .values(
                is_active=False,
                status="inactive",
            )
        )
        await db.execute(stmt)

    async def activate_version(
            self,
            *,
            prompt_version: PromptVersion,
    ) -> PromptVersion:
        """
        激活指定版本对象。
        """

        prompt_version.is_active = True
        prompt_version.status = "active"
        return prompt_version

    async def deactivate_version(
            self,
            *,
            prompt_version: PromptVersion,
    ) -> PromptVersion:
        """
        停用指定版本对象。
        """

        prompt_version.is_active = False
        prompt_version.status = "inactive"
        return prompt_version

    async def get_active_version_by_template_id(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            template_id: UUID,
    ) -> PromptVersion | None:
        """
        查询某个模板当前启用版本。
        """

        stmt = select(PromptVersion).where(
            PromptVersion.tenant_id == tenant_id,
            PromptVersion.template_id == template_id,
            PromptVersion.deleted_at.is_(None),
            PromptVersion.is_active.is_(True),
            PromptVersion.status == "active",
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_version_by_template_key(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            template_key: str,
    ) -> tuple[PromptTemplate, PromptVersion] | None:
        """
        根据 template_key 查询当前启用 Prompt 版本。
        """

        stmt = (
            select(PromptTemplate, PromptVersion)
            .join(PromptVersion, PromptVersion.template_id == PromptTemplate.id)
            .where(
                PromptTemplate.tenant_id == tenant_id,
                PromptTemplate.template_key == template_key,
                PromptTemplate.deleted_at.is_(None),
                PromptTemplate.status == "active",
                PromptVersion.tenant_id == tenant_id,
                PromptVersion.deleted_at.is_(None),
                PromptVersion.is_active.is_(True),
                PromptVersion.status == "active",
            )
        )
        result = await db.execute(stmt)
        row = result.one_or_none()
        if row is None:
            return None

        return row[0], row[1]

    async def get_active_version_by_scene(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            scene: str,
    ) -> tuple[PromptTemplate, PromptVersion] | None:
        """
        根据 scene 查询当前启用 Prompt 版本。

        注意：
        - 如果同一 scene 下存在多个 active 模板，该方法按创建时间倒序取最新模板；
        - 后续如果要强约束 scene 唯一，需要总控确认是否新增唯一索引。
        """

        stmt = (
            select(PromptTemplate, PromptVersion)
            .join(PromptVersion, PromptVersion.template_id == PromptTemplate.id)
            .where(
                PromptTemplate.tenant_id == tenant_id,
                PromptTemplate.scene == scene,
                PromptTemplate.deleted_at.is_(None),
                PromptTemplate.status == "active",
                PromptVersion.tenant_id == tenant_id,
                PromptVersion.deleted_at.is_(None),
                PromptVersion.is_active.is_(True),
                PromptVersion.status == "active",
            )
            .order_by(PromptTemplate.created_at.desc(), PromptVersion.version.desc())
            .limit(1)
        )
        result = await db.execute(stmt)
        row = result.one_or_none()
        if row is None:
            return None

        return row[0], row[1]
