# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/05/03 22:34
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.operation_copilot import BIQueryResult
from app.services.metric_service import MetricService
from app.services.sql_guard_service import SqlGuardService
from app.tools.base import ToolResult


class BITools:
    """运营 Copilot 可调用 BI 工具。

    工具层负责：
    - 查询指标口径；
    - 构造指标 SQL；
    - SQL Guard；
    - 只读 SQL 执行。

    注意：执行 SQL 前必须先 guard。
    """

    def __init__(
            self,
            *,
            db: AsyncSession,
            metric_service: MetricService | None = None,
            sql_guard_service: SqlGuardService | None = None,
            max_rows: int = 100,
    ) -> None:
        self.db = db
        self.metric_service = metric_service or MetricService()
        self.sql_guard_service = sql_guard_service or SqlGuardService()
        self.max_rows = max_rows

    async def list_metrics(self) -> ToolResult:
        metrics = [
            item.model_dump(mode="json")
            for item in self.metric_service.list_metrics()
        ]
        return ToolResult.ok(
            tool_name="list_metrics",
            data={"metrics": metrics},
        )

    async def get_metric_definition(self, *, metric_key: str) -> ToolResult:
        metric = self.metric_service.get_metric(metric_key)
        if metric is None:
            return ToolResult.fail(
                tool_name="get_metric_definition",
                error_code="METRIC_NOT_FOUND",
                error_message=f"指标不存在：{metric_key}",
            )

        return ToolResult.ok(
            tool_name="get_metric_definition",
            data=metric.model_dump(mode="json"),
        )

    async def build_metric_query(
            self,
            *,
            metric_key: str,
            tenant_id: UUID,
            context: dict[str, Any] | None = None,
    ) -> ToolResult:
        plan = self.metric_service.build_metric_query(
            metric_key=metric_key,
            tenant_id=tenant_id,
            context=context or {},
        )

        if plan.status != "available":
            return ToolResult.fail(
                tool_name="build_metric_query",
                error_code=plan.status.upper(),
                error_message=plan.unavailable_reason or "指标当前不可查询。",
                data=plan.model_dump(mode="json"),
            )

        return ToolResult.ok(
            tool_name="build_metric_query",
            data=plan.model_dump(mode="json"),
        )

    async def guard_sql(self, *, sql: str) -> ToolResult:
        result = self.sql_guard_service.guard(sql)
        if not result.passed:
            return ToolResult.fail(
                tool_name="guard_sql",
                error_code=result.error_code or "SQL_GUARD_REJECTED",
                error_message=result.rejected_reason or "SQL 未通过安全检查。",
                data=result.model_dump(mode="json"),
            )

        return ToolResult.ok(
            tool_name="guard_sql",
            data=result.model_dump(mode="json"),
        )

    async def execute_readonly_sql(
            self,
            *,
            sql: str,
            params: dict[str, Any] | None = None,
            max_rows: int | None = None,
    ) -> ToolResult:
        guard_result = self.sql_guard_service.guard(sql)
        if not guard_result.passed or not guard_result.normalized_sql:
            return ToolResult.fail(
                tool_name="execute_readonly_sql",
                error_code=guard_result.error_code or "SQL_GUARD_REJECTED",
                error_message=guard_result.rejected_reason or "SQL 未通过安全检查。",
                data=guard_result.model_dump(mode="json"),
            )

        limit = min(max_rows or self.max_rows, self.max_rows)
        execute_params = dict(params or {})
        execute_params["__limit"] = limit

        wrapped_sql = f"""
        SELECT *
        FROM (
            {guard_result.normalized_sql.rstrip(";")}
        ) AS operation_copilot_readonly_query
        LIMIT :__limit
        """

        result = await self.db.execute(text(wrapped_sql), execute_params)
        rows = [
            {key: _to_jsonable(value) for key, value in row.items()}
            for row in result.mappings().all()
        ]

        columns = list(rows[0].keys()) if rows else []
        query_result = BIQueryResult(
            columns=columns,
            rows=rows,
            row_count=len(rows),
            limited=len(rows) >= limit,
            max_rows=limit,
        )

        return ToolResult.ok(
            tool_name="execute_readonly_sql",
            data={
                "guard": guard_result.model_dump(mode="json"),
                "query_result": query_result.model_dump(mode="json"),
            },
        )


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    return value
