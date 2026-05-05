# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/05/03 22:35
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from uuid import UUID

from app.services.metric_service import MetricService

TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")


def test_list_metrics_contains_core_metrics() -> None:
    service = MetricService()

    keys = {item.metric_key for item in service.list_metrics()}

    assert "gmv" in keys
    assert "order_count" in keys
    assert "avg_order_value" in keys
    assert "inventory_stock" in keys
    assert "low_stock_sku_count" in keys
    assert "conversion_rate" in keys


def test_build_gmv_query_contains_tenant_filter() -> None:
    service = MetricService()

    plan = service.build_metric_query(
        metric_key="gmv",
        tenant_id=TENANT_ID,
        context={},
    )

    assert plan.status == "available"
    assert plan.sql is not None
    assert "order_info" in plan.sql
    assert "tenant_id = :tenant_id" in plan.sql
    assert plan.params["tenant_id"] == str(TENANT_ID)


def test_build_inventory_query_uses_product_sku() -> None:
    service = MetricService()

    plan = service.build_metric_query(
        metric_key="inventory_stock",
        tenant_id=TENANT_ID,
        context={},
    )

    assert plan.status == "available"
    assert plan.sql is not None
    assert "product_sku" in plan.sql
    assert "product p" in plan.sql
    assert "tenant_id = :tenant_id" in plan.sql


def test_conversion_rate_is_registered_but_not_calculated() -> None:
    service = MetricService()

    metric = service.get_metric("conversion_rate")
    assert metric is not None
    assert metric.status == "data_source_missing"

    plan = service.build_metric_query(
        metric_key="conversion_rate",
        tenant_id=TENANT_ID,
        context={},
    )

    assert plan.status == "data_source_missing"
    assert plan.sql is None
    assert plan.unavailable_reason is not None
    assert "不能用订单数或用户数伪造转化率" in plan.unavailable_reason


def test_unknown_metric_returns_not_found_plan() -> None:
    service = MetricService()

    plan = service.build_metric_query(
        metric_key="unknown_metric",
        tenant_id=TENANT_ID,
        context={},
    )

    assert plan.status == "not_found"
    assert plan.sql is None
