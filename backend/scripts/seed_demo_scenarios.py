# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/27 11:19
IDE       :PyCharm
作者      :董宏升

执行窗口 2：Demo 场景种子数据脚本。

用途：
- 补充少量边界场景数据
- 支撑执行窗口 3 之后验证商品状态、库存、订单状态、售后状态、评价情感、会员等级等查询逻辑

覆盖场景：
- inactive 商品
- 低库存 SKU
- 待发货订单
- 不同售后状态
- negative 评价
- 普通会员用户

运行方式：
    cd backend
    python scripts/seed_demo_scenarios.py

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
from app.models.order import OrderInfo, OrderItem
from app.models.product import Product, ProductReview, ProductSku
from app.models.ticket import AfterSaleTicket
from app.models.user import UserProfile

TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")

NORMAL_USER_ID = uuid.UUID("11000000-0000-0000-0000-000000000001")

INACTIVE_PRODUCT_ID = uuid.UUID("22000000-0000-0000-0000-000000000001")
INACTIVE_SKU_ID = uuid.UUID("22100000-0000-0000-0000-000000000001")

LOW_STOCK_PRODUCT_ID = uuid.UUID("23000000-0000-0000-0000-000000000001")
LOW_STOCK_SKU_ID = uuid.UUID("23100000-0000-0000-0000-000000000001")

PENDING_SHIPMENT_ORDER_ID = uuid.UUID("33000000-0000-0000-0000-000000000001")
PENDING_SHIPMENT_ORDER_ITEM_ID = uuid.UUID("33100000-0000-0000-0000-000000000001")

NEGATIVE_REVIEW_ID = uuid.UUID("34000000-0000-0000-0000-000000000001")

AFTER_SALE_PENDING_ID = uuid.UUID("41000000-0000-0000-0000-000000000001")
AFTER_SALE_APPROVED_ID = uuid.UUID("42000000-0000-0000-0000-000000000001")
AFTER_SALE_REJECTED_ID = uuid.UUID("43000000-0000-0000-0000-000000000001")
AFTER_SALE_COMPLETED_ID = uuid.UUID("44000000-0000-0000-0000-000000000001")


async def seed_demo_scenarios() -> None:
    async with AsyncSessionLocal() as session:
        seed_markers = [
            ("normal_user", UserProfile, NORMAL_USER_ID),
            ("inactive_product", Product, INACTIVE_PRODUCT_ID),
            ("inactive_sku", ProductSku, INACTIVE_SKU_ID),
            ("low_stock_product", Product, LOW_STOCK_PRODUCT_ID),
            ("low_stock_sku", ProductSku, LOW_STOCK_SKU_ID),
            ("pending_shipment_order", OrderInfo, PENDING_SHIPMENT_ORDER_ID),
            ("pending_shipment_order_item", OrderItem, PENDING_SHIPMENT_ORDER_ITEM_ID),
            ("negative_review", ProductReview, NEGATIVE_REVIEW_ID),
            ("after_sale_pending", AfterSaleTicket, AFTER_SALE_PENDING_ID),
            ("after_sale_approved", AfterSaleTicket, AFTER_SALE_APPROVED_ID),
            ("after_sale_rejected", AfterSaleTicket, AFTER_SALE_REJECTED_ID),
            ("after_sale_completed", AfterSaleTicket, AFTER_SALE_COMPLETED_ID),
        ]

        existing_items: list[str] = []
        missing_items: list[str] = []

        for marker_name, model_cls, record_id in seed_markers:
            existed = await session.scalar(
                select(model_cls.id).where(model_cls.id == record_id)
            )
            if existed is None:
                missing_items.append(marker_name)
            else:
                existing_items.append(marker_name)

        if len(existing_items) == len(seed_markers):
            print("Demo scenario seed data already exists, skipped.")
            return

        if existing_items and missing_items:
            raise RuntimeError(
                "Demo scenario seed data is partially inserted. "
                f"existing_items={existing_items}, missing_items={missing_items}. "
                "Please inspect the database and clean the partial seed data before rerunning."
            )

        now = datetime.now(timezone.utc)

        normal_user = UserProfile(
            id=NORMAL_USER_ID,
            tenant_id=TENANT_ID,
            user_no="U200001",
            nickname="普通会员小林",
            phone_masked="139****0002",
            email_masked="normal****@example.com",
            gender="unknown",
            member_level="normal",
            city="上海",
            preference_json={
                "categories": ["digital", "home"],
                "price_sensitivity": "high",
            },
            tag_json=["普通会员", "价格敏感"],
            remark="Demo 场景：普通会员用户",
        )

        inactive_product = Product(
            id=INACTIVE_PRODUCT_ID,
            tenant_id=TENANT_ID,
            product_no="P200001",
            title="已下架智能香薰机",
            subtitle="Demo 场景：inactive 商品",
            brand="OmniHome",
            category="smart_home",
            category_path="家居/智能设备/香薰机",
            description="用于验证 inactive 商品是否会被业务查询正确过滤或标记。",
            main_image_url="https://example.com/products/P200001/main.png",
            status="inactive",
            tag_json=["已下架", "Demo"],
            attribute_json={"capacity": "300ml", "wifi": True},
            metadata_json={"seed": True, "scenario": "inactive_product"},
        )

        inactive_sku = ProductSku(
            id=INACTIVE_SKU_ID,
            tenant_id=TENANT_ID,
            product_id=INACTIVE_PRODUCT_ID,
            sku_no="SKU200001",
            sku_name="灰色基础版",
            sku_code="P200001-GRAY-BASIC",
            sale_price=Decimal("129.00"),
            market_price=Decimal("169.00"),
            cost_price=Decimal("80.00"),
            currency="CNY",
            stock_quantity=20,
            image_url="https://example.com/products/P200001/gray.png",
            status="inactive",
            spec_json={"color": "gray", "version": "basic"},
            metadata_json={"seed": True, "scenario": "inactive_sku"},
        )

        low_stock_product = Product(
            id=LOW_STOCK_PRODUCT_ID,
            tenant_id=TENANT_ID,
            product_no="P200002",
            title="低库存蓝牙降噪耳机",
            subtitle="Demo 场景：低库存 SKU",
            brand="OmniAudio",
            category="digital",
            category_path="数码/音频/蓝牙耳机",
            description="用于验证低库存商品查询、导购推荐和库存提醒逻辑。",
            main_image_url="https://example.com/products/P200002/main.png",
            status="active",
            tag_json=["低库存", "数码", "耳机"],
            attribute_json={"noise_canceling": True, "battery_life": "30h"},
            metadata_json={"seed": True, "scenario": "low_stock"},
        )

        low_stock_sku = ProductSku(
            id=LOW_STOCK_SKU_ID,
            tenant_id=TENANT_ID,
            product_id=LOW_STOCK_PRODUCT_ID,
            sku_no="SKU200002",
            sku_name="黑色 Pro 版",
            sku_code="P200002-BLACK-PRO",
            sale_price=Decimal("399.00"),
            market_price=Decimal("499.00"),
            cost_price=Decimal("260.00"),
            currency="CNY",
            stock_quantity=2,
            image_url="https://example.com/products/P200002/black-pro.png",
            status="active",
            spec_json={"color": "black", "version": "pro"},
            metadata_json={"seed": True, "scenario": "low_stock_sku"},
        )

        pending_order = OrderInfo(
            id=PENDING_SHIPMENT_ORDER_ID,
            tenant_id=TENANT_ID,
            order_no="O200001",
            user_id=NORMAL_USER_ID,
            order_status="paid",
            payment_status="paid",
            fulfillment_status="unfulfilled",
            total_amount=Decimal("399.00"),
            discount_amount=Decimal("30.00"),
            paid_amount=Decimal("369.00"),
            currency="CNY",
            receiver_snapshot_json={
                "name": "林**",
                "phone": "139****0002",
                "city": "上海",
            },
            payment_snapshot_json={
                "method": "alipay",
                "transaction_no": "mock_txn_200001",
            },
            logistics_snapshot_json={
                "carrier": None,
                "tracking_no": None,
                "status": "pending_shipment",
            },
            metadata_json={"seed": True, "scenario": "pending_shipment_order"},
            placed_at=now,
            paid_at=now,
        )

        pending_order_item = OrderItem(
            id=PENDING_SHIPMENT_ORDER_ITEM_ID,
            tenant_id=TENANT_ID,
            order_id=PENDING_SHIPMENT_ORDER_ID,
            product_id=LOW_STOCK_PRODUCT_ID,
            sku_id=LOW_STOCK_SKU_ID,
            product_title_snapshot="低库存蓝牙降噪耳机",
            sku_name_snapshot="黑色 Pro 版",
            sku_spec_snapshot_json={"color": "black", "version": "pro"},
            quantity=1,
            unit_price=Decimal("399.00"),
            total_amount=Decimal("399.00"),
            discount_amount=Decimal("30.00"),
            paid_amount=Decimal("369.00"),
            item_status="normal",
            metadata_json={"seed": True, "scenario": "pending_shipment_order_item"},
        )

        negative_review = ProductReview(
            id=NEGATIVE_REVIEW_ID,
            tenant_id=TENANT_ID,
            product_id=LOW_STOCK_PRODUCT_ID,
            sku_id=LOW_STOCK_SKU_ID,
            user_id=NORMAL_USER_ID,
            order_item_id=PENDING_SHIPMENT_ORDER_ITEM_ID,
            rating=2,
            content="耳机降噪效果没有预期好，佩戴时间长了有点不舒服。",
            image_json=[],
            sentiment="negative",
            status="visible",
            metadata_json={"seed": True, "scenario": "negative_review"},
        )

        after_sale_pending = AfterSaleTicket(
            id=AFTER_SALE_PENDING_ID,
            tenant_id=TENANT_ID,
            ticket_no="AS200001",
            user_id=NORMAL_USER_ID,
            order_id=PENDING_SHIPMENT_ORDER_ID,
            order_item_id=PENDING_SHIPMENT_ORDER_ITEM_ID,
            after_sale_type="refund",
            reason="待审核退款申请",
            description="Demo 场景：pending 售后状态。",
            status="pending",
            refund_amount=Decimal("369.00"),
            currency="CNY",
            evidence_json=[],
            audit_snapshot_json={"risk_level": "medium"},
            metadata_json={"seed": True, "scenario": "after_sale_pending"},
            submitted_at=now,
        )

        after_sale_approved = AfterSaleTicket(
            id=AFTER_SALE_APPROVED_ID,
            tenant_id=TENANT_ID,
            ticket_no="AS200002",
            user_id=NORMAL_USER_ID,
            order_id=PENDING_SHIPMENT_ORDER_ID,
            order_item_id=PENDING_SHIPMENT_ORDER_ITEM_ID,
            after_sale_type="refund",
            reason="已通过退款申请",
            description="Demo 场景：approved 售后状态。",
            status="approved",
            refund_amount=Decimal("369.00"),
            currency="CNY",
            evidence_json=[],
            audit_snapshot_json={"risk_level": "low", "approved_by": "demo_operator"},
            metadata_json={"seed": True, "scenario": "after_sale_approved"},
            submitted_at=now,
        )

        after_sale_rejected = AfterSaleTicket(
            id=AFTER_SALE_REJECTED_ID,
            tenant_id=TENANT_ID,
            ticket_no="AS200003",
            user_id=NORMAL_USER_ID,
            order_id=PENDING_SHIPMENT_ORDER_ID,
            order_item_id=PENDING_SHIPMENT_ORDER_ITEM_ID,
            after_sale_type="return",
            reason="不符合退货条件",
            description="Demo 场景：rejected 售后状态。",
            status="rejected",
            refund_amount=Decimal("0.00"),
            currency="CNY",
            evidence_json=[],
            audit_snapshot_json={"risk_level": "low", "reject_reason": "超过可退条件"},
            metadata_json={"seed": True, "scenario": "after_sale_rejected"},
            submitted_at=now,
            resolved_at=now,
        )

        after_sale_completed = AfterSaleTicket(
            id=AFTER_SALE_COMPLETED_ID,
            tenant_id=TENANT_ID,
            ticket_no="AS200004",
            user_id=NORMAL_USER_ID,
            order_id=PENDING_SHIPMENT_ORDER_ID,
            order_item_id=PENDING_SHIPMENT_ORDER_ITEM_ID,
            after_sale_type="refund",
            reason="退款已完成",
            description="Demo 场景：completed 售后状态。",
            status="completed",
            refund_amount=Decimal("369.00"),
            currency="CNY",
            evidence_json=[],
            audit_snapshot_json={"risk_level": "low", "completed_by": "demo_operator"},
            metadata_json={"seed": True, "scenario": "after_sale_completed"},
            submitted_at=now,
            resolved_at=now,
        )

        session.add_all(
            [
                normal_user,
                inactive_product,
                inactive_sku,
                low_stock_product,
                low_stock_sku,
                pending_order,
                pending_order_item,
                negative_review,
                after_sale_pending,
                after_sale_approved,
                after_sale_rejected,
                after_sale_completed,
            ]
        )

        await session.commit()

        print("Demo scenario seed data inserted successfully.")
        print(f"tenant_id={TENANT_ID}")


if __name__ == "__main__":
    asyncio.run(seed_demo_scenarios())
