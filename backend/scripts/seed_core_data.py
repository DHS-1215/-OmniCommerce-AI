# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/27 10:52
IDE       :PyCharm
作者      :董宏升

执行窗口 2：核心数据模型种子数据脚本。
- 初始化一批核心验证种子数据
- 覆盖用户、商品、SKU、评价、订单、售后、工单、知识库、Prompt、模型调用日志、Agent 日志、评测等核心链路

注意：
- 本脚本不实现业务接口
- 本脚本不调用模型
- 本脚本不执行 Agent / RAG 流程
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
import asyncio
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select

import app.models  # noqa: F401
from app.db.session import AsyncSessionLocal
from app.models.agent import AgentStepLog, AgentTask, ToolCallLog
from app.models.evaluation import EvaluationCase, EvaluationResult
from app.models.knowledge import KnowledgeChunk, KnowledgeDocument
from app.models.llm import ModelCallLog
from app.models.order import OrderInfo, OrderItem
from app.models.product import Product, ProductReview, ProductSku
from app.models.prompt import PromptTemplate, PromptVersion
from app.models.ticket import AfterSaleTicket, CustomerServiceTicket
from app.models.user import UserProfile

TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")

USER_ID = uuid.UUID("10000000-0000-0000-0000-000000000001")
PRODUCT_ID = uuid.UUID("20000000-0000-0000-0000-000000000001")
SKU_ID = uuid.UUID("21000000-0000-0000-0000-000000000001")
ORDER_ID = uuid.UUID("30000000-0000-0000-0000-000000000001")
ORDER_ITEM_ID = uuid.UUID("31000000-0000-0000-0000-000000000001")
REVIEW_ID = uuid.UUID("32000000-0000-0000-0000-000000000001")
AFTER_SALE_ID = uuid.UUID("40000000-0000-0000-0000-000000000001")
AGENT_TASK_ID = uuid.UUID("50000000-0000-0000-0000-000000000001")
AGENT_STEP_LOG_ID = uuid.UUID("51000000-0000-0000-0000-000000000001")
TOOL_CALL_LOG_ID = uuid.UUID("52000000-0000-0000-0000-000000000001")
CUSTOMER_SERVICE_TICKET_ID = uuid.UUID("53000000-0000-0000-0000-000000000001")
KNOWLEDGE_DOCUMENT_ID = uuid.UUID("60000000-0000-0000-0000-000000000001")
KNOWLEDGE_CHUNK_ID = uuid.UUID("61000000-0000-0000-0000-000000000001")
PROMPT_TEMPLATE_ID = uuid.UUID("70000000-0000-0000-0000-000000000001")
PROMPT_VERSION_ID = uuid.UUID("71000000-0000-0000-0000-000000000001")
MODEL_CALL_LOG_ID = uuid.UUID("80000000-0000-0000-0000-000000000001")
EVALUATION_CASE_ID = uuid.UUID("90000000-0000-0000-0000-000000000001")
EVALUATION_RESULT_ID = uuid.UUID("91000000-0000-0000-0000-000000000001")


async def seed() -> None:
    async with AsyncSessionLocal() as session:
        seed_markers = [
            ("user_profile", UserProfile, USER_ID),
            ("product", Product, PRODUCT_ID),
            ("product_sku", ProductSku, SKU_ID),
            ("order_info", OrderInfo, ORDER_ID),
            ("order_item", OrderItem, ORDER_ITEM_ID),
            ("product_review", ProductReview, REVIEW_ID),
            ("after_sale_ticket", AfterSaleTicket, AFTER_SALE_ID),
            ("agent_task", AgentTask, AGENT_TASK_ID),
            ("agent_step_log", AgentStepLog, AGENT_STEP_LOG_ID),
            ("tool_call_log", ToolCallLog, TOOL_CALL_LOG_ID),
            ("customer_service_ticket", CustomerServiceTicket, CUSTOMER_SERVICE_TICKET_ID),
            ("knowledge_document", KnowledgeDocument, KNOWLEDGE_DOCUMENT_ID),
            ("knowledge_chunk", KnowledgeChunk, KNOWLEDGE_CHUNK_ID),
            ("prompt_template", PromptTemplate, PROMPT_TEMPLATE_ID),
            ("prompt_version", PromptVersion, PROMPT_VERSION_ID),
            ("model_call_log", ModelCallLog, MODEL_CALL_LOG_ID),
            ("evaluation_case", EvaluationCase, EVALUATION_CASE_ID),
            ("evaluation_result", EvaluationResult, EVALUATION_RESULT_ID),
        ]

        existing_tables: list[str] = []
        missing_tables: list[str] = []

        for table_name, model_cls, record_id in seed_markers:
            existed = await session.scalar(
                select(model_cls.id).where(model_cls.id == record_id)
            )
            if existed is None:
                missing_tables.append(table_name)
            else:
                existing_tables.append(table_name)

        if len(existing_tables) == len(seed_markers):
            print("Core verification seed data already exists, skipped.")
            return

        if existing_tables and missing_tables:
            raise RuntimeError(
                "Core verification seed data is partially inserted. "
                f"existing_tables={existing_tables}, missing_tables={missing_tables}. "
                "Please inspect the database and clean the partial seed data before rerunning."
            )

        now = datetime.now(timezone.utc)

        user = UserProfile(
            id=USER_ID,
            tenant_id=TENANT_ID,
            user_no="U100001",
            nickname="测试用户小智",
            phone_masked="138****0001",
            email_masked="test****@example.com",
            gender="unknown",
            member_level="gold",
            city="杭州",
            preference_json={
                "categories": ["smart_home", "kitchen"],
                "price_sensitivity": "medium",
            },
            tag_json=["高复购", "偏好智能家居"],
            remark="执行窗口 2 种子用户",
        )

        product = Product(
            id=PRODUCT_ID,
            tenant_id=TENANT_ID,
            product_no="P100001",
            title="智营智能恒温电热水壶",
            subtitle="支持多档控温，适合家庭与办公室",
            brand="OmniHome",
            category="smart_home",
            category_path="家电/厨房小电/电热水壶",
            description="一款用于演示商品查询、导购推荐和客服咨询的测试商品。",
            main_image_url="https://example.com/products/P100001/main.png",
            status="active",
            tag_json=["智能家居", "厨房电器", "热销"],
            attribute_json={
                "capacity": "1.7L",
                "temperature_control": True,
                "material": "304 stainless steel",
            },
            metadata_json={"seed": True},
        )

        sku = ProductSku(
            id=SKU_ID,
            tenant_id=TENANT_ID,
            product_id=PRODUCT_ID,
            sku_no="SKU100001",
            sku_name="白色标准版",
            sku_code="P100001-WHITE-STD",
            sale_price=Decimal("199.00"),
            market_price=Decimal("259.00"),
            cost_price=Decimal("120.00"),
            currency="CNY",
            stock_quantity=100,
            image_url="https://example.com/products/P100001/white.png",
            status="active",
            spec_json={"color": "white", "version": "standard"},
            metadata_json={"seed": True},
        )

        order = OrderInfo(
            id=ORDER_ID,
            tenant_id=TENANT_ID,
            order_no="O100001",
            user_id=USER_ID,
            order_status="completed",
            payment_status="paid",
            fulfillment_status="delivered",
            total_amount=Decimal("199.00"),
            discount_amount=Decimal("20.00"),
            paid_amount=Decimal("179.00"),
            currency="CNY",
            receiver_snapshot_json={
                "name": "董**",
                "phone": "138****0001",
                "city": "杭州",
            },
            payment_snapshot_json={
                "method": "wechat_pay",
                "transaction_no": "mock_txn_100001",
            },
            logistics_snapshot_json={
                "carrier": "SF Express",
                "tracking_no": "SF****0001",
                "status": "delivered",
            },
            metadata_json={"seed": True},
            placed_at=now,
            paid_at=now,
        )

        order_item = OrderItem(
            id=ORDER_ITEM_ID,
            tenant_id=TENANT_ID,
            order_id=ORDER_ID,
            product_id=PRODUCT_ID,
            sku_id=SKU_ID,
            product_title_snapshot="智营智能恒温电热水壶",
            sku_name_snapshot="白色标准版",
            sku_spec_snapshot_json={"color": "white", "version": "standard"},
            quantity=1,
            unit_price=Decimal("199.00"),
            total_amount=Decimal("199.00"),
            discount_amount=Decimal("20.00"),
            paid_amount=Decimal("179.00"),
            item_status="normal",
            metadata_json={"seed": True},
        )

        review = ProductReview(
            id=REVIEW_ID,
            tenant_id=TENANT_ID,
            product_id=PRODUCT_ID,
            sku_id=SKU_ID,
            user_id=USER_ID,
            order_item_id=ORDER_ITEM_ID,
            rating=5,
            content="控温很方便，烧水速度也不错，客服响应很快。",
            image_json=[],
            sentiment="positive",
            status="visible",
            metadata_json={"seed": True},
        )

        after_sale_ticket = AfterSaleTicket(
            id=AFTER_SALE_ID,
            tenant_id=TENANT_ID,
            ticket_no="AS100001",
            user_id=USER_ID,
            order_id=ORDER_ID,
            order_item_id=ORDER_ITEM_ID,
            after_sale_type="refund",
            reason="测试售后原因",
            description="用于执行窗口 3 售后查询与创建逻辑验证。",
            status="pending",
            refund_amount=Decimal("179.00"),
            currency="CNY",
            evidence_json=[],
            audit_snapshot_json={"risk_level": "low"},
            metadata_json={"seed": True},
            submitted_at=now,
        )

        agent_task = AgentTask(
            id=AGENT_TASK_ID,
            tenant_id=TENANT_ID,
            request_id="req_seed_agent_001",
            user_id=USER_ID,
            agent_type="customer_service",
            session_id="seed_session_001",
            task_no="AT100001",
            input_summary="用户询问订单和售后政策",
            output_summary="系统识别为售后咨询并建议创建工单",
            status="success",
            intent="after_sale_consultation",
            handoff_required=False,
            latency_ms=1200,
            metadata_json={"seed": True},
        )

        agent_step_log = AgentStepLog(
            id=AGENT_STEP_LOG_ID,
            tenant_id=TENANT_ID,
            request_id="req_seed_agent_001",
            agent_task_id=AGENT_TASK_ID,
            step_name="intent_detection",
            step_order=1,
            input_summary="订单是否可以退款？",
            output_summary="after_sale_consultation",
            status="success",
            latency_ms=120,
            metadata_json={"seed": True},
        )

        tool_call_log = ToolCallLog(
            id=TOOL_CALL_LOG_ID,
            tenant_id=TENANT_ID,
            request_id="req_seed_agent_001",
            agent_task_id=AGENT_TASK_ID,
            agent_step_log_id=AGENT_STEP_LOG_ID,
            tool_name="get_order_detail",
            tool_type="business",
            input_summary="order_no=O100001",
            output_summary="订单已完成，已支付，已送达",
            status="success",
            latency_ms=80,
            metadata_json={"seed": True},
        )

        customer_service_ticket = CustomerServiceTicket(
            id=CUSTOMER_SERVICE_TICKET_ID,
            tenant_id=TENANT_ID,
            ticket_no="CS100001",
            user_id=USER_ID,
            order_id=ORDER_ID,
            source="agent",
            channel="web",
            category="aftersale",
            priority="normal",
            status="open",
            title="用户咨询订单售后",
            content="用户咨询订单 O100001 是否可以退款。",
            assigned_operator_id=None,
            resolution=None,
            related_agent_task_id=AGENT_TASK_ID,
            metadata_json={"seed": True},
            opened_at=now,
        )

        knowledge_document = KnowledgeDocument(
            id=KNOWLEDGE_DOCUMENT_ID,
            tenant_id=TENANT_ID,
            document_no="KD100001",
            title="智营商城售后政策示例文档",
            source_type="manual",
            source_uri=None,
            storage_object_key=None,
            mime_type="text/markdown",
            file_size=1024,
            status="indexed",
            parser_status="success",
            language="zh-CN",
            acl_json={"roles": ["customer_service", "operator"]},
            metadata_json={"seed": True},
        )

        knowledge_chunk = KnowledgeChunk(
            id=KNOWLEDGE_CHUNK_ID,
            tenant_id=TENANT_ID,
            document_id=KNOWLEDGE_DOCUMENT_ID,
            chunk_no="KD100001-C001",
            title="智营商城售后政策示例文档",
            source_type="manual",
            content="商品签收后 7 天内，如未影响二次销售，可申请无理由退货。特殊商品以页面说明为准。",
            content_hash="seed_chunk_hash_001",
            page_no=1,
            section_title="七天无理由退货",
            token_count=42,
            keywords_json=["售后", "退款", "七天无理由"],
            embedding_id="seed_embedding_001",
            vector_collection="knowledge_chunks",
            metadata_json={"seed": True},
        )

        prompt_template = PromptTemplate(
            id=PROMPT_TEMPLATE_ID,
            tenant_id=TENANT_ID,
            template_key="customer_service_intent",
            name="客服意图识别 Prompt",
            scene="customer_service_intent",
            description="用于识别客服场景下用户意图的默认 Prompt。",
            status="active",
            metadata_json={"seed": True},
        )

        prompt_version = PromptVersion(
            id=PROMPT_VERSION_ID,
            tenant_id=TENANT_ID,
            template_id=PROMPT_TEMPLATE_ID,
            version=1,
            content=(
                "你是电商客服意图识别助手。"
                "请根据用户输入识别意图，输出结构化 JSON。"
            ),
            variable_schema_json={
                "type": "object",
                "properties": {
                    "user_input": {"type": "string"},
                    "conversation_context": {"type": "string"},
                },
                "required": ["user_input"],
            },
            model_config_json={
                "temperature": 0.2,
                "max_tokens": 512,
            },
            gray_config_json=None,
            is_active=True,
            status="active",
            change_log="初始化默认版本",
        )

        model_call_log = ModelCallLog(
            id=MODEL_CALL_LOG_ID,
            tenant_id=TENANT_ID,
            request_id="req_seed_model_001",
            user_id=USER_ID,
            provider="openai_compatible",
            model_name="qwen-plus",
            model_type="llm",
            call_type="chat",
            prompt_template_id=PROMPT_TEMPLATE_ID,
            prompt_version_id=PROMPT_VERSION_ID,
            input_tokens=120,
            output_tokens=80,
            total_tokens=200,
            cost_amount=Decimal("0.000000"),
            currency="CNY",
            latency_ms=900,
            status="success",
            input_summary="用户询问售后政策",
            output_summary="识别为售后咨询",
            metadata_json={"seed": True},
        )

        evaluation_case = EvaluationCase(
            id=EVALUATION_CASE_ID,
            tenant_id=TENANT_ID,
            case_no="EV100001",
            case_type="rag",
            name="售后政策 RAG 回答评测",
            description="验证 RAG 是否能基于售后政策文档回答退款规则。",
            input_json={
                "question": "签收后几天内可以无理由退货？"
            },
            expected_output_json={
                "answer_contains": ["7 天", "无理由退货"]
            },
            reference_context_json=[
                {
                    "document_no": "KD100001",
                    "chunk_no": "KD100001-C001",
                }
            ],
            tags_json=["rag", "aftersale", "policy"],
            status="active",
            metadata_json={"seed": True},
        )

        evaluation_result = EvaluationResult(
            id=EVALUATION_RESULT_ID,
            tenant_id=TENANT_ID,
            request_id="req_seed_eval_001",
            case_id=EVALUATION_CASE_ID,
            run_no="RUN100001",
            target_type="rag",
            target_id="seed_rag_strategy",
            status="success",
            score=Decimal("0.9500"),
            answer_relevance=Decimal("0.9600"),
            faithfulness=Decimal("0.9500"),
            context_recall=Decimal("0.9400"),
            context_precision=Decimal("0.9300"),
            tool_call_success_rate=None,
            agent_task_success_rate=None,
            latency_ms=1100,
            token_cost=Decimal("0.000000"),
            input_summary="签收后几天内可以无理由退货？",
            output_summary="回答包含 7 天无理由退货，并引用售后政策文档。",
            metrics_json={
                "answer_relevance": 0.96,
                "faithfulness": 0.95,
                "context_recall": 0.94,
                "context_precision": 0.93,
            },
            metadata_json={"seed": True},
        )

        session.add_all(
            [
                user,
                product,
                sku,
                order,
                order_item,
                review,
                after_sale_ticket,
                agent_task,
                agent_step_log,
                tool_call_log,
                customer_service_ticket,
                knowledge_document,
                knowledge_chunk,
                prompt_template,
                prompt_version,
                model_call_log,
                evaluation_case,
                evaluation_result,
            ]
        )

        await session.commit()
        print("Core verification seed data inserted successfully.")
        print(f"tenant_id={TENANT_ID}")


if __name__ == "__main__":
    asyncio.run(seed())
