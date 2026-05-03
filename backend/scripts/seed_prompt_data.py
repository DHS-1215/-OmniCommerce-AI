# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/05/01 11:38
IDE       :PyCharm
作者      :董宏升

默认 Prompt 种子数据脚本。

本脚本负责：
- 初始化 Prompt 模板；
- 初始化 Prompt v1 版本；
- 默认将 v1 设置为 active；
- 为后续 RAG / Agent / BI / 内容生成提供可读取 Prompt。

注意：
- 不调用模型网关；
- 不实现 Agent / RAG；
- 不覆盖已存在的 Prompt 内容；
- 如果模板已存在且已有 active 版本，则跳过；
- 如果模板已存在但没有 active 版本，则补充一个新的 active 版本。
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
import asyncio
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.prompt import PromptTemplate, PromptVersion


DEFAULT_TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")


@dataclass(frozen=True)
class DefaultPromptSeed:
    """
    默认 Prompt 种子定义。
    """

    template_key: str
    name: str
    scene: str
    description: str
    content: str
    variable_schema_json: dict[str, Any]
    model_config_json: dict[str, Any] | None = None
    gray_config_json: dict[str, Any] | None = None
    metadata_json: dict[str, Any] | None = None


DEFAULT_PROMPTS: list[DefaultPromptSeed] = [
    DefaultPromptSeed(
        template_key="cs_intent_default",
        name="客服意图识别默认 Prompt",
        scene="customer_service_intent",
        description="用于识别用户当前客服意图，例如商品咨询、订单查询、售后申请、投诉转人工。",
        content="""你是电商智能客服的意图识别助手。

请根据用户消息和历史对话摘要，判断用户当前最主要的意图。

可选意图：
- product_consultation：商品咨询
- order_query：订单查询
- after_sale_request：售后申请
- complaint：投诉
- human_handoff：需要人工介入
- general_question：普通问题

用户消息：
{{user_message}}

历史对话摘要：
{{conversation_summary}}

请只输出 JSON，不要输出额外解释。
输出格式：
{
  "intent": "order_query",
  "confidence": 0.90,
  "reason": "用户询问订单发货状态"
}
""",
        variable_schema_json={
            "required": ["user_message", "conversation_summary"],
            "properties": {
                "user_message": {
                    "type": "string",
                    "required": True,
                    "description": "用户当前消息",
                },
                "conversation_summary": {
                    "type": "string",
                    "required": True,
                    "description": "历史对话摘要，没有则传空字符串",
                },
            },
        },
        model_config_json={
            "provider": "mock",
            "model": "mock-chat-model",
            "temperature": 0.1,
            "max_tokens": 512,
        },
        gray_config_json={
            "enabled": False,
            "strategy": "none",
        },
        metadata_json={
            "owner": "customer_service",
            "risk_level": "medium",
        },
    ),
    DefaultPromptSeed(
        template_key="cs_answer_default",
        name="客服回答生成默认 Prompt",
        scene="customer_service_answer",
        description="用于客服 Agent 基于业务工具结果和知识库内容生成用户可读回答。",
        content="""你是电商平台的智能客服助手。

回答要求：
1. 语气礼貌、清楚、简洁；
2. 只能基于提供的业务信息回答；
3. 如果信息不足，说明需要进一步核实；
4. 涉及退款、赔付、投诉、隐私信息时，建议转人工；
5. 不要编造订单、物流、退款或政策信息。

用户问题：
{{user_question}}

用户画像摘要：
{{user_profile}}

订单 / 售后 / 工单上下文：
{{business_context}}

知识库政策上下文：
{{policy_context}}

请生成给用户的最终回复。
""",
        variable_schema_json={
            "required": [
                "user_question",
                "user_profile",
                "business_context",
                "policy_context",
            ],
            "properties": {
                "user_question": {
                    "type": "string",
                    "required": True,
                    "description": "用户问题",
                },
                "user_profile": {
                    "type": "string",
                    "required": True,
                    "description": "用户画像摘要",
                },
                "business_context": {
                    "type": "string",
                    "required": True,
                    "description": "订单、售后、工单等业务上下文",
                },
                "policy_context": {
                    "type": "string",
                    "required": True,
                    "description": "知识库政策上下文",
                },
            },
        },
        model_config_json={
            "provider": "mock",
            "model": "mock-chat-model",
            "temperature": 0.3,
            "max_tokens": 1024,
        },
        gray_config_json={
            "enabled": False,
            "strategy": "none",
        },
        metadata_json={
            "owner": "customer_service",
            "risk_level": "high",
        },
    ),
    DefaultPromptSeed(
        template_key="rag_answer_generation_default",
        name="RAG 回答生成默认 Prompt",
        scene="rag_answer_generation",
        description="用于企业知识库 RAG 基于召回上下文生成带引用约束的回答。",
        content="""你是企业知识库问答助手。

回答规则：
1. 必须优先依据给定知识库上下文回答；
2. 如果上下文没有答案，请明确说明“当前资料中未找到依据”；
3. 不要编造政策、流程、金额、时效；
4. 回答中要尽量保留来源线索；
5. 对不确定内容给出保守表述。

用户问题：
{{question}}

知识库上下文：
{{context}}

引用规则：
{{citation_rules}}

请生成最终回答。
""",
        variable_schema_json={
            "required": ["question", "context", "citation_rules"],
            "properties": {
                "question": {
                    "type": "string",
                    "required": True,
                    "description": "用户问题",
                },
                "context": {
                    "type": "string",
                    "required": True,
                    "description": "RAG 检索召回上下文",
                },
                "citation_rules": {
                    "type": "string",
                    "required": True,
                    "description": "引用格式和来源要求",
                },
            },
        },
        model_config_json={
            "provider": "mock",
            "model": "mock-chat-model",
            "temperature": 0.2,
            "max_tokens": 1200,
        },
        gray_config_json={
            "enabled": False,
            "strategy": "none",
        },
        metadata_json={
            "owner": "rag",
            "risk_level": "high",
        },
    ),
    DefaultPromptSeed(
        template_key="shopping_guide_recommendation_default",
        name="智能导购推荐默认 Prompt",
        scene="shopping_guide_recommendation",
        description="用于智能导购基于用户需求、预算、偏好和候选商品生成推荐理由。",
        content="""你是电商平台的智能导购助手。

你的目标是帮助用户做购买决策，而不是盲目推销。

用户需求：
{{user_need}}

用户预算：
{{budget}}

用户偏好：
{{user_preference}}

候选商品信息：
{{candidate_products}}

请输出：
1. 推荐商品排序；
2. 每个商品的推荐理由；
3. 适合人群；
4. 需要提醒用户注意的缺点；
5. 最终购买建议。

请保持表达真实、克制，不要夸大商品效果。
""",
        variable_schema_json={
            "required": [
                "user_need",
                "budget",
                "user_preference",
                "candidate_products",
            ],
            "properties": {
                "user_need": {
                    "type": "string",
                    "required": True,
                    "description": "用户购买需求",
                },
                "budget": {
                    "type": "string",
                    "required": True,
                    "description": "用户预算",
                },
                "user_preference": {
                    "type": "string",
                    "required": True,
                    "description": "用户偏好",
                },
                "candidate_products": {
                    "type": "string",
                    "required": True,
                    "description": "候选商品摘要",
                },
            },
        },
        model_config_json={
            "provider": "mock",
            "model": "mock-chat-model",
            "temperature": 0.4,
            "max_tokens": 1200,
        },
        gray_config_json={
            "enabled": False,
            "strategy": "none",
        },
        metadata_json={
            "owner": "shopping_guide",
            "risk_level": "medium",
        },
    ),
    DefaultPromptSeed(
        template_key="text_to_sql_default",
        name="Text-to-SQL 默认 Prompt",
        scene="text_to_sql",
        description="用于运营 Copilot 将自然语言指标问题转换为只读 SQL。",
        content="""你是电商运营分析系统的 Text-to-SQL 助手。

安全规则：
1. 只能生成 SELECT 查询；
2. 禁止生成 INSERT、UPDATE、DELETE、DROP、TRUNCATE、ALTER；
3. 必须遵守指标口径定义；
4. 不确定字段含义时不要猜测；
5. SQL 需要尽量可读。

用户问题：
{{question}}

指标口径定义：
{{metric_definitions}}

可用表结构：
{{table_schema}}

请只输出 SQL，不要输出解释。
""",
        variable_schema_json={
            "required": ["question", "metric_definitions", "table_schema"],
            "properties": {
                "question": {
                    "type": "string",
                    "required": True,
                    "description": "运营人员自然语言问题",
                },
                "metric_definitions": {
                    "type": "string",
                    "required": True,
                    "description": "指标口径定义",
                },
                "table_schema": {
                    "type": "string",
                    "required": True,
                    "description": "允许查询的表结构",
                },
            },
        },
        model_config_json={
            "provider": "mock",
            "model": "mock-chat-model",
            "temperature": 0.0,
            "max_tokens": 800,
        },
        gray_config_json={
            "enabled": False,
            "strategy": "none",
        },
        metadata_json={
            "owner": "operation_copilot",
            "risk_level": "high",
        },
    ),
    DefaultPromptSeed(
        template_key="operation_report_generation_default",
        name="运营报告生成默认 Prompt",
        scene="operation_report_generation",
        description="用于运营 Copilot 基于指标结果生成运营分析报告。",
        content="""你是电商运营分析助手。

请根据业务背景和指标结果，生成结构化运营分析报告。

业务背景：
{{business_context}}

指标结果：
{{analysis_result}}

报告要求：
{{report_requirement}}

请输出：
1. 核心结论；
2. 数据发现；
3. 可能原因；
4. 运营建议；
5. 风险和不确定性。

不要编造未提供的数据。
""",
        variable_schema_json={
            "required": [
                "business_context",
                "analysis_result",
                "report_requirement",
            ],
            "properties": {
                "business_context": {
                    "type": "string",
                    "required": True,
                    "description": "业务背景",
                },
                "analysis_result": {
                    "type": "string",
                    "required": True,
                    "description": "指标查询或分析结果",
                },
                "report_requirement": {
                    "type": "string",
                    "required": True,
                    "description": "报告生成要求",
                },
            },
        },
        model_config_json={
            "provider": "mock",
            "model": "mock-chat-model",
            "temperature": 0.3,
            "max_tokens": 1600,
        },
        gray_config_json={
            "enabled": False,
            "strategy": "none",
        },
        metadata_json={
            "owner": "operation_copilot",
            "risk_level": "medium",
        },
    ),
    DefaultPromptSeed(
        template_key="content_generation_default",
        name="内容生成默认 Prompt",
        scene="content_generation",
        description="用于商品标题、卖点、详情页和活动文案生成。",
        content="""你是电商内容运营助手。

请根据商品信息和活动信息生成营销文案。

商品信息：
{{product_info}}

活动信息：
{{campaign_info}}

目标语气：
{{tone}}

生成要求：
{{generation_requirement}}

请输出候选文案，并说明每条文案适合的使用位置。
不要使用绝对化、虚假承诺或无法证明的表达。
""",
        variable_schema_json={
            "required": [
                "product_info",
                "campaign_info",
                "tone",
                "generation_requirement",
            ],
            "properties": {
                "product_info": {
                    "type": "string",
                    "required": True,
                    "description": "商品信息",
                },
                "campaign_info": {
                    "type": "string",
                    "required": True,
                    "description": "活动信息",
                },
                "tone": {
                    "type": "string",
                    "required": True,
                    "description": "目标语气",
                },
                "generation_requirement": {
                    "type": "string",
                    "required": True,
                    "description": "生成要求",
                },
            },
        },
        model_config_json={
            "provider": "mock",
            "model": "mock-chat-model",
            "temperature": 0.6,
            "max_tokens": 1200,
        },
        gray_config_json={
            "enabled": False,
            "strategy": "none",
        },
        metadata_json={
            "owner": "content",
            "risk_level": "medium",
        },
    ),
    DefaultPromptSeed(
        template_key="content_review_default",
        name="内容审核默认 Prompt",
        scene="content_review",
        description="用于商品和活动文案的敏感词、品牌规则和合规风险审核。",
        content="""你是电商内容审核助手。

请审核以下文案是否存在风险。

待审核内容：
{{content}}

品牌规则：
{{brand_rules}}

敏感词规则：
{{sensitive_word_rules}}

审核要求：
1. 判断是否通过；
2. 标出风险词或风险句；
3. 说明风险原因；
4. 给出修改建议。

请只输出 JSON，不要输出额外解释。
输出格式：
{
  "passed": false,
  "risks": [
    {
      "text": "风险片段",
      "reason": "风险原因",
      "suggestion": "修改建议"
    }
  ]
}
""",
        variable_schema_json={
            "required": [
                "content",
                "brand_rules",
                "sensitive_word_rules",
            ],
            "properties": {
                "content": {
                    "type": "string",
                    "required": True,
                    "description": "待审核文案",
                },
                "brand_rules": {
                    "type": "string",
                    "required": True,
                    "description": "品牌规则",
                },
                "sensitive_word_rules": {
                    "type": "string",
                    "required": True,
                    "description": "敏感词规则",
                },
            },
        },
        model_config_json={
            "provider": "mock",
            "model": "mock-chat-model",
            "temperature": 0.1,
            "max_tokens": 1000,
        },
        gray_config_json={
            "enabled": False,
            "strategy": "none",
        },
        metadata_json={
            "owner": "content",
            "risk_level": "high",
        },
    ),
]


async def get_template_by_key(
        db: AsyncSession,
        *,
        tenant_id: UUID,
        template_key: str,
) -> PromptTemplate | None:
    stmt = select(PromptTemplate).where(
        PromptTemplate.tenant_id == tenant_id,
        PromptTemplate.template_key == template_key,
        PromptTemplate.deleted_at.is_(None),
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_active_version(
        db: AsyncSession,
        *,
        tenant_id: UUID,
        template_id: UUID,
) -> PromptVersion | None:
    stmt = select(PromptVersion).where(
        PromptVersion.tenant_id == tenant_id,
        PromptVersion.template_id == template_id,
        PromptVersion.deleted_at.is_(None),
        PromptVersion.is_active.is_(True),
        PromptVersion.status == "active",
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_next_version_number(
        db: AsyncSession,
        *,
        tenant_id: UUID,
        template_id: UUID,
) -> int:
    stmt = select(func.max(PromptVersion.version)).where(
        PromptVersion.tenant_id == tenant_id,
        PromptVersion.template_id == template_id,
    )
    max_version = await db.scalar(stmt)
    return int(max_version or 0) + 1


async def seed_one_prompt(
        db: AsyncSession,
        *,
        seed: DefaultPromptSeed,
) -> str:
    """
    写入单个默认 Prompt。

    返回：
        created_template
        created_version
        skipped
    """

    template = await get_template_by_key(
        db,
        tenant_id=DEFAULT_TENANT_ID,
        template_key=seed.template_key,
    )

    if template is None:
        template = PromptTemplate(
            tenant_id=DEFAULT_TENANT_ID,
            template_key=seed.template_key,
            name=seed.name,
            scene=seed.scene,
            description=seed.description,
            status="active",
            metadata_json=seed.metadata_json,
        )
        db.add(template)
        await db.flush()

        version = PromptVersion(
            tenant_id=DEFAULT_TENANT_ID,
            template_id=template.id,
            version=1,
            content=seed.content,
            variable_schema_json=seed.variable_schema_json,
            model_config_json=seed.model_config_json,
            gray_config_json=seed.gray_config_json,
            is_active=True,
            status="active",
            change_log="默认 Prompt 种子版本 v1",
        )
        db.add(version)
        return "created_template"

    active_version = await get_active_version(
        db,
        tenant_id=DEFAULT_TENANT_ID,
        template_id=template.id,
    )
    if active_version is not None:
        return "skipped"

    next_version = await get_next_version_number(
        db,
        tenant_id=DEFAULT_TENANT_ID,
        template_id=template.id,
    )

    version = PromptVersion(
        tenant_id=DEFAULT_TENANT_ID,
        template_id=template.id,
        version=next_version,
        content=seed.content,
        variable_schema_json=seed.variable_schema_json,
        model_config_json=seed.model_config_json,
        gray_config_json=seed.gray_config_json,
        is_active=True,
        status="active",
        change_log="补充默认 Prompt active 版本",
    )
    db.add(version)
    return "created_version"


async def main() -> None:
    created_template_count = 0
    created_version_count = 0
    skipped_count = 0

    async with AsyncSessionLocal() as db:
        try:
            for seed in DEFAULT_PROMPTS:
                result = await seed_one_prompt(
                    db,
                    seed=seed,
                )

                if result == "created_template":
                    created_template_count += 1
                    print(f"[created_template] {seed.template_key} -> {seed.scene}")
                elif result == "created_version":
                    created_version_count += 1
                    print(f"[created_version] {seed.template_key} -> {seed.scene}")
                else:
                    skipped_count += 1
                    print(f"[skipped] {seed.template_key} already has active version")

            await db.commit()

        except Exception:
            await db.rollback()
            raise

    print("")
    print("Prompt seed finished.")
    print(f"created_template_count = {created_template_count}")
    print(f"created_version_count  = {created_version_count}")
    print(f"skipped_count          = {skipped_count}")


if __name__ == "__main__":
    asyncio.run(main())