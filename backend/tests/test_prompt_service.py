# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/05/01 14:22
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from uuid import UUID, uuid4

import pytest

from app.core.exceptions import BaseAppException
from app.db.session import AsyncSessionLocal, engine
from app.schemas.prompt import (
    PromptRenderRequest,
    PromptTemplateCreate,
    PromptVersionCreate,
)
from app.services.prompt_service import PromptService

TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")


@pytest.fixture
async def dispose_engine_after_test():
    """
    避免 SQLAlchemy async engine 连接池中的 asyncpg 连接跨事件循环复用。
    """
    await engine.dispose()
    yield
    await engine.dispose()


@pytest.mark.anyio
async def test_prompt_service_create_version_and_render(dispose_engine_after_test) -> None:
    service = PromptService()
    template_key = f"pytest_prompt_{uuid4().hex}"

    async with AsyncSessionLocal() as db:
        template = await service.create_template(
            db,
            payload=PromptTemplateCreate(
                tenant_id=TENANT_ID,
                template_key=template_key,
                name="pytest Prompt 模板",
                scene="pytest_prompt_scene",
                description="pytest 创建的 Prompt 模板",
                metadata_json={"source": "pytest"},
            ),
        )

        version = await service.create_version(
            db,
            template_id=template.id,
            payload=PromptVersionCreate(
                tenant_id=TENANT_ID,
                content="你好，{{user_name}}，你的问题是：{{question}}",
                variable_schema_json={
                    "required": ["user_name", "question"],
                    "properties": {
                        "user_name": {
                            "type": "string",
                            "required": True,
                        },
                        "question": {
                            "type": "string",
                            "required": True,
                        },
                    },
                },
                model_config_json={
                    "provider": "mock",
                    "model": "mock-chat-model",
                },
                gray_config_json={
                    "enabled": False,
                },
                is_active=True,
                change_log="pytest 初始版本",
            ),
        )

        assert version.version == 1
        assert version.status == "active"
        assert version.is_active is True

        rendered = await service.render_prompt(
            db,
            payload=PromptRenderRequest(
                tenant_id=TENANT_ID,
                template_key=template_key,
                variables={
                    "user_name": "张三",
                    "question": "订单什么时候发货？",
                },
            ),
        )

        assert rendered.template_key == template_key
        assert rendered.version == 1
        assert "张三" in rendered.rendered_content
        assert "订单什么时候发货？" in rendered.rendered_content
        assert "{{user_name}}" not in rendered.rendered_content
        assert "{{question}}" not in rendered.rendered_content


@pytest.mark.anyio
async def test_prompt_service_render_missing_variable(dispose_engine_after_test) -> None:
    service = PromptService()
    template_key = f"pytest_prompt_missing_{uuid4().hex}"

    async with AsyncSessionLocal() as db:
        template = await service.create_template(
            db,
            payload=PromptTemplateCreate(
                tenant_id=TENANT_ID,
                template_key=template_key,
                name="pytest 缺变量测试 Prompt",
                scene="pytest_prompt_missing_scene",
                description="pytest 缺变量测试",
                metadata_json={"source": "pytest"},
            ),
        )

        await service.create_version(
            db,
            template_id=template.id,
            payload=PromptVersionCreate(
                tenant_id=TENANT_ID,
                content="用户：{{user_name}}，问题：{{question}}",
                variable_schema_json={
                    "required": ["user_name", "question"],
                },
                is_active=True,
                change_log="pytest 缺变量测试版本",
            ),
        )

        with pytest.raises(BaseAppException) as exc_info:
            await service.render_prompt(
                db,
                payload=PromptRenderRequest(
                    tenant_id=TENANT_ID,
                    template_key=template_key,
                    variables={
                        "user_name": "李四",
                    },
                ),
            )

        assert exc_info.value.code == "PROMPT_RENDER_VARIABLE_MISSING"
        assert "question" in exc_info.value.data["missing_variables"]
