# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/05/01 08:54
IDE       :PyCharm
作者      :董宏升

Prompt 管理模块 Schema。

本文件只负责：
- Prompt 模板请求 / 响应结构；
- Prompt 版本请求 / 响应结构；
- Prompt 渲染请求 / 响应结构；
- Prompt 列表分页查询结构。

注意：
- 不写数据库查询；
- 不写业务逻辑；
- 不调用模型网关；
- 不硬编码具体 Agent Prompt。
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.schemas.common import JsonDict, ORMBaseModel, PageQuery, TenantRequest

PromptTemplateStatus = Literal["active", "inactive", "archived"]
PromptVersionStatus = Literal["draft", "active", "inactive", "archived"]


class PromptTemplateListQuery(PageQuery):
    """
    Prompt 模板分页查询参数。

    当前认证 / RBAC 尚未实现，因此继续显式传 tenant_id。
    """

    tenant_id: UUID = Field(..., description="租户 ID")
    scene: str | None = Field(default=None, description="Prompt 场景")
    status: PromptTemplateStatus | None = Field(
        default=None,
        description="模板状态，不传则查询全部状态",
    )
    keyword: str | None = Field(
        default=None,
        min_length=1,
        max_length=128,
        description="关键词，匹配 template_key / name / scene",
    )


class PromptTemplateCreate(TenantRequest):
    """
    创建 Prompt 模板请求。
    """

    template_key: str = Field(
        ...,
        min_length=2,
        max_length=128,
        description="模板唯一业务 Key，同一租户下不可重复",
    )
    name: str = Field(
        ...,
        min_length=2,
        max_length=255,
        description="模板名称",
    )
    scene: str = Field(
        ...,
        min_length=2,
        max_length=128,
        description="Prompt 场景，例如 customer_service_intent/rag_answer_generation",
    )
    description: str | None = Field(
        default=None,
        max_length=2000,
        description="模板说明",
    )
    metadata_json: JsonDict | None = Field(
        default=None,
        description="扩展元数据 JSON",
    )


class PromptTemplateUpdate(TenantRequest):
    """
    更新 Prompt 模板请求。

    只更新传入字段；未传字段保持不变。
    """

    name: str | None = Field(
        default=None,
        min_length=2,
        max_length=255,
        description="模板名称",
    )
    scene: str | None = Field(
        default=None,
        min_length=2,
        max_length=128,
        description="Prompt 场景",
    )
    description: str | None = Field(
        default=None,
        max_length=2000,
        description="模板说明",
    )
    status: PromptTemplateStatus | None = Field(
        default=None,
        description="模板状态",
    )
    metadata_json: JsonDict | None = Field(
        default=None,
        description="扩展元数据 JSON",
    )


class PromptTemplateResponse(ORMBaseModel):
    """
    Prompt 模板响应。
    """

    id: UUID = Field(..., description="模板主键 ID")
    tenant_id: UUID = Field(..., description="租户 ID")

    template_key: str = Field(..., description="模板唯一业务 Key")
    name: str = Field(..., description="模板名称")
    scene: str = Field(..., description="Prompt 场景")
    description: str | None = Field(default=None, description="模板说明")
    status: str = Field(..., description="模板状态")
    metadata_json: JsonDict | None = Field(default=None, description="扩展元数据 JSON")

    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


class PromptVersionListQuery(PageQuery):
    """
    Prompt 版本分页查询参数。
    """

    tenant_id: UUID = Field(..., description="租户 ID")
    status: PromptVersionStatus | None = Field(
        default=None,
        description="版本状态，不传则查询全部状态",
    )


class PromptVersionCreate(TenantRequest):
    """
    创建 Prompt 版本请求。

    如果 is_active=true，service 层会自动停用同模板下其他版本。
    """

    content: str = Field(
        ...,
        min_length=1,
        description="Prompt 模板内容，变量使用 {{variable_name}} 形式",
    )
    variable_schema_json: JsonDict | None = Field(
        default=None,
        description="变量 Schema JSON，用于声明必填变量、变量类型和说明",
    )
    model_config_json: JsonDict | None = Field(
        default=None,
        description="推荐模型参数 JSON，例如 temperature/top_p/max_tokens",
    )
    gray_config_json: JsonDict | None = Field(
        default=None,
        description="灰度配置 JSON 预留",
    )
    is_active: bool = Field(
        default=False,
        description="是否创建后立即启用该版本",
    )
    change_log: str | None = Field(
        default=None,
        max_length=2000,
        description="版本变更说明",
    )


class PromptVersionUpdate(TenantRequest):
    """
    更新 Prompt 版本请求。

    一般只建议更新 draft / inactive 版本。
    active 版本如需变更，建议创建新版本，方便追踪历史。
    """

    content: str | None = Field(
        default=None,
        min_length=1,
        description="Prompt 模板内容",
    )
    variable_schema_json: JsonDict | None = Field(
        default=None,
        description="变量 Schema JSON",
    )
    model_config_json: JsonDict | None = Field(
        default=None,
        description="推荐模型参数 JSON",
    )
    gray_config_json: JsonDict | None = Field(
        default=None,
        description="灰度配置 JSON 预留",
    )
    status: PromptVersionStatus | None = Field(
        default=None,
        description="版本状态",
    )
    change_log: str | None = Field(
        default=None,
        max_length=2000,
        description="版本变更说明",
    )


class PromptVersionResponse(ORMBaseModel):
    """
    Prompt 版本响应。
    """

    id: UUID = Field(..., description="版本主键 ID")
    tenant_id: UUID = Field(..., description="租户 ID")
    template_id: UUID = Field(..., description="Prompt 模板 ID")

    version: int = Field(..., ge=1, description="版本号")
    content: str = Field(..., description="Prompt 模板内容")
    variable_schema_json: JsonDict | None = Field(
        default=None,
        description="变量 Schema JSON",
    )
    model_config_json: JsonDict | None = Field(
        default=None,
        description="推荐模型参数 JSON",
    )
    gray_config_json: JsonDict | None = Field(
        default=None,
        description="灰度配置 JSON 预留",
    )
    is_active: bool = Field(..., description="是否当前启用版本")
    status: str = Field(..., description="版本状态")
    change_log: str | None = Field(default=None, description="版本变更说明")

    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


class PromptTemplateDetailResponse(PromptTemplateResponse):
    """
    Prompt 模板详情响应。
    """

    versions: list[PromptVersionResponse] = Field(
        default_factory=list,
        description="Prompt 版本列表",
    )


class PromptActiveVersionResponse(BaseModel):
    """
    当前启用 Prompt 版本响应。

    给后续 RAG / Agent / 内容生成模块读取 Prompt 使用。
    """

    template: PromptTemplateResponse = Field(..., description="Prompt 模板")
    version: PromptVersionResponse = Field(..., description="当前启用版本")


class PromptRenderRequest(TenantRequest):
    """
    Prompt 渲染请求。

    支持两种定位方式：
    - template_key：精确指定模板；
    - scene：按场景获取当前启用版本。

    二者至少传一个。
    """

    template_key: str | None = Field(
        default=None,
        min_length=2,
        max_length=128,
        description="模板唯一业务 Key",
    )
    scene: str | None = Field(
        default=None,
        min_length=2,
        max_length=128,
        description="Prompt 场景",
    )
    version: int | None = Field(
        default=None,
        ge=1,
        description="指定版本号；不传则使用当前启用版本",
    )
    variables: JsonDict = Field(
        default_factory=dict,
        description="渲染变量",
    )

    @model_validator(mode="after")
    def validate_render_target(self) -> "PromptRenderRequest":
        if not self.template_key and not self.scene:
            raise ValueError("template_key 和 scene 至少需要传一个")
        return self


class PromptRenderResponse(BaseModel):
    """
    Prompt 渲染响应。

    返回 rendered_content 的同时，保留模板 ID / 版本 ID，
    方便后续模型调用日志记录 prompt_template_id / prompt_version_id。
    """

    template_id: UUID = Field(..., description="Prompt 模板 ID")
    version_id: UUID = Field(..., description="Prompt 版本 ID")

    template_key: str = Field(..., description="模板唯一业务 Key")
    scene: str = Field(..., description="Prompt 场景")
    version: int = Field(..., description="版本号")

    rendered_content: str = Field(..., description="渲染后的 Prompt 内容")
    variables: JsonDict = Field(default_factory=dict, description="本次渲染变量")

    model_config_json: JsonDict | None = Field(
        default=None,
        description="推荐模型参数 JSON",
    )
    gray_config_json: JsonDict | None = Field(
        default=None,
        description="灰度配置 JSON",
    )
