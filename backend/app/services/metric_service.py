# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/05/03 22:33
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from app.schemas.operation_copilot import MetricDefinitionResponse, MetricQueryPlan


@dataclass(frozen=True)
class MetricDefinition:
    metric_key: str
    name: str
    description: str
    category: str
    formula: str | None
    source_tables: tuple[str, ...]
    dimensions: tuple[str, ...] = field(default_factory=tuple)
    filters: tuple[str, ...] = field(default_factory=tuple)
    status: str = "available"
    unavailable_reason: str | None = None


class MetricService:
    """运营指标口径服务。

    第一版按总控裁决使用代码内置指标口径，不新增 metric_definition 表。
    注意：conversion_rate 只注册，不硬算；当前缺少曝光/访问/点击/加购等行为数据源。
    """

    LOW_STOCK_THRESHOLD = 5

    def __init__(self) -> None:
        self._metrics: dict[str, MetricDefinition] = {
            "gmv": MetricDefinition(
                metric_key="gmv",
                name="GMV",
                description="已支付订单的实付金额汇总。",
                category="sales",
                formula="sum(order_info.paid_amount)",
                source_tables=("order_info",),
                filters=("payment_status = paid", "deleted_at is null", "tenant_id"),
            ),
            "order_count": MetricDefinition(
                metric_key="order_count",
                name="订单数",
                description="已支付订单数量。",
                category="sales",
                formula="count(order_info.id)",
                source_tables=("order_info",),
                filters=("payment_status = paid", "deleted_at is null", "tenant_id"),
            ),
            "avg_order_value": MetricDefinition(
                metric_key="avg_order_value",
                name="客单价",
                description="GMV / 已支付订单数。",
                category="sales",
                formula="sum(order_info.paid_amount) / count(order_info.id)",
                source_tables=("order_info",),
                filters=("payment_status = paid", "deleted_at is null", "tenant_id"),
            ),
            "inventory_stock": MetricDefinition(
                metric_key="inventory_stock",
                name="总库存",
                description="在售商品 active SKU 的库存总量。",
                category="inventory",
                formula="sum(product_sku.stock_quantity)",
                source_tables=("product", "product_sku"),
                filters=("product.status = active", "product_sku.status = active", "deleted_at is null", "tenant_id"),
            ),
            "low_stock_sku_count": MetricDefinition(
                metric_key="low_stock_sku_count",
                name="低库存 SKU 数",
                description=f"库存小于等于 {self.LOW_STOCK_THRESHOLD} 的在售 SKU 数。",
                category="inventory",
                formula=f"count(product_sku.id where stock_quantity <= {self.LOW_STOCK_THRESHOLD})",
                source_tables=("product", "product_sku"),
                filters=("product.status = active", "product_sku.status = active", "deleted_at is null", "tenant_id"),
            ),
            "refund_amount": MetricDefinition(
                metric_key="refund_amount",
                name="退款金额",
                description="售后单中的退款金额汇总。",
                category="aftersale",
                formula="sum(after_sale_ticket.refund_amount)",
                source_tables=("after_sale_ticket",),
                filters=("deleted_at is null", "tenant_id"),
            ),
            "after_sale_count": MetricDefinition(
                metric_key="after_sale_count",
                name="售后单数",
                description="售后单数量。",
                category="aftersale",
                formula="count(after_sale_ticket.id)",
                source_tables=("after_sale_ticket",),
                filters=("deleted_at is null", "tenant_id"),
            ),
            "review_count": MetricDefinition(
                metric_key="review_count",
                name="评价数",
                description="可见商品评价数量。",
                category="review",
                formula="count(product_review.id)",
                source_tables=("product_review",),
                filters=("status = visible", "deleted_at is null", "tenant_id"),
            ),
            "positive_review_count": MetricDefinition(
                metric_key="positive_review_count",
                name="正向评价数",
                description="可见且 sentiment=positive 的商品评价数量。",
                category="review",
                formula="count(product_review.id where sentiment = positive)",
                source_tables=("product_review",),
                filters=("status = visible", "sentiment = positive", "deleted_at is null", "tenant_id"),
            ),
            "negative_review_count": MetricDefinition(
                metric_key="negative_review_count",
                name="负向评价数",
                description="可见且 sentiment=negative 的商品评价数量。",
                category="review",
                formula="count(product_review.id where sentiment = negative)",
                source_tables=("product_review",),
                filters=("status = visible", "sentiment = negative", "deleted_at is null", "tenant_id"),
            ),
            "conversion_rate": MetricDefinition(
                metric_key="conversion_rate",
                name="转化率",
                description="注册指标，但第一版不计算。当前缺少曝光、访问、点击、加购等行为数据源。",
                category="conversion",
                formula=None,
                source_tables=(),
                status="data_source_missing",
                unavailable_reason="当前核心表缺少曝光、访问、点击、加购等行为数据源，不能用订单数或用户数伪造转化率。",
            ),
        }

    def list_metrics(self) -> list[MetricDefinitionResponse]:
        return [
            self._to_response(metric)
            for metric in self._metrics.values()
        ]

    def get_metric(self, metric_key: str) -> MetricDefinitionResponse | None:
        metric = self._metrics.get(metric_key)
        if metric is None:
            return None
        return self._to_response(metric)

    def build_metric_query(
        self,
        *,
        metric_key: str,
        tenant_id: UUID,
        context: dict[str, Any] | None = None,
    ) -> MetricQueryPlan:
        metric = self._metrics.get(metric_key)
        if metric is None:
            return MetricQueryPlan(
                metric_key=metric_key,
                metric_name=metric_key,
                status="not_found",
                unavailable_reason="指标不存在或尚未注册。",
            )

        if metric.status != "available":
            return MetricQueryPlan(
                metric_key=metric.metric_key,
                metric_name=metric.name,
                status=metric.status,
                source_tables=list(metric.source_tables),
                unavailable_reason=metric.unavailable_reason,
            )

        sql, params = self._build_sql(metric_key=metric_key, tenant_id=tenant_id, context=context or {})
        return MetricQueryPlan(
            metric_key=metric.metric_key,
            metric_name=metric.name,
            status="available",
            sql=sql,
            params=params,
            source_tables=list(metric.source_tables),
        )

    def _build_sql(
        self,
        *,
        metric_key: str,
        tenant_id: UUID,
        context: dict[str, Any],
    ) -> tuple[str, dict[str, Any]]:
        params: dict[str, Any] = {"tenant_id": str(tenant_id)}
        date_filter = self._date_filter(context=context, params=params)

        if metric_key == "gmv":
            return (
                f"""
                SELECT COALESCE(SUM(paid_amount), 0) AS gmv
                FROM order_info
                WHERE tenant_id = :tenant_id
                  AND deleted_at IS NULL
                  AND payment_status = 'paid'
                  {date_filter}
                """,
                params,
            )

        if metric_key == "order_count":
            return (
                f"""
                SELECT COUNT(id) AS order_count
                FROM order_info
                WHERE tenant_id = :tenant_id
                  AND deleted_at IS NULL
                  AND payment_status = 'paid'
                  {date_filter}
                """,
                params,
            )

        if metric_key == "avg_order_value":
            return (
                f"""
                SELECT
                    CASE
                        WHEN COUNT(id) = 0 THEN 0
                        ELSE COALESCE(SUM(paid_amount), 0) / COUNT(id)
                    END AS avg_order_value
                FROM order_info
                WHERE tenant_id = :tenant_id
                  AND deleted_at IS NULL
                  AND payment_status = 'paid'
                  {date_filter}
                """,
                params,
            )

        if metric_key == "inventory_stock":
            return (
                """
                SELECT COALESCE(SUM(ps.stock_quantity), 0) AS inventory_stock
                FROM product_sku ps
                JOIN product p ON p.id = ps.product_id
                WHERE ps.tenant_id = :tenant_id
                  AND p.tenant_id = :tenant_id
                  AND ps.deleted_at IS NULL
                  AND p.deleted_at IS NULL
                  AND ps.status = 'active'
                  AND p.status = 'active'
                """,
                params,
            )

        if metric_key == "low_stock_sku_count":
            params["low_stock_threshold"] = self.LOW_STOCK_THRESHOLD
            return (
                """
                SELECT COUNT(ps.id) AS low_stock_sku_count
                FROM product_sku ps
                JOIN product p ON p.id = ps.product_id
                WHERE ps.tenant_id = :tenant_id
                  AND p.tenant_id = :tenant_id
                  AND ps.deleted_at IS NULL
                  AND p.deleted_at IS NULL
                  AND ps.status = 'active'
                  AND p.status = 'active'
                  AND ps.stock_quantity <= :low_stock_threshold
                """,
                params,
            )

        if metric_key == "refund_amount":
            return (
                """
                SELECT COALESCE(SUM(refund_amount), 0) AS refund_amount
                FROM after_sale_ticket
                WHERE tenant_id = :tenant_id
                  AND deleted_at IS NULL
                """,
                params,
            )

        if metric_key == "after_sale_count":
            return (
                """
                SELECT COUNT(id) AS after_sale_count
                FROM after_sale_ticket
                WHERE tenant_id = :tenant_id
                  AND deleted_at IS NULL
                """,
                params,
            )

        if metric_key == "review_count":
            return (
                """
                SELECT COUNT(id) AS review_count
                FROM product_review
                WHERE tenant_id = :tenant_id
                  AND deleted_at IS NULL
                  AND status = 'visible'
                """,
                params,
            )

        if metric_key == "positive_review_count":
            return (
                """
                SELECT COUNT(id) AS positive_review_count
                FROM product_review
                WHERE tenant_id = :tenant_id
                  AND deleted_at IS NULL
                  AND status = 'visible'
                  AND sentiment = 'positive'
                """,
                params,
            )

        if metric_key == "negative_review_count":
            return (
                """
                SELECT COUNT(id) AS negative_review_count
                FROM product_review
                WHERE tenant_id = :tenant_id
                  AND deleted_at IS NULL
                  AND status = 'visible'
                  AND sentiment = 'negative'
                """,
                params,
            )

        return (
            """
            SELECT 1 AS unsupported_metric
            WHERE tenant_id = :tenant_id
            """,
            params,
        )

    def _date_filter(self, *, context: dict[str, Any], params: dict[str, Any]) -> str:
        date_range = context.get("date_range") or {}
        start = date_range.get("start")
        end = date_range.get("end")

        parts: list[str] = []
        if start:
            params["start_date"] = start
            parts.append("AND placed_at >= :start_date")
        if end:
            params["end_date"] = end
            parts.append("AND placed_at < :end_date")

        return "\n".join(parts)

    def _to_response(self, metric: MetricDefinition) -> MetricDefinitionResponse:
        return MetricDefinitionResponse(
            metric_key=metric.metric_key,
            name=metric.name,
            description=metric.description,
            category=metric.category,
            formula=metric.formula,
            source_tables=list(metric.source_tables),
            dimensions=list(metric.dimensions),
            filters=list(metric.filters),
            status=metric.status,
            unavailable_reason=metric.unavailable_reason,
        )