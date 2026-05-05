# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/05/04 09:00
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from uuid import UUID

import pytest

from app.db.session import AsyncSessionLocal
from app.tools.bi_tools import BITools

TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")


@pytest.mark.anyio
async def test_bi_tools_build_and_execute_gmv_query() -> None:
    async with AsyncSessionLocal() as db:
        tools = BITools(db=db, max_rows=20)

        build_result = await tools.build_metric_query(
            metric_key="gmv",
            tenant_id=TENANT_ID,
            context={},
        )
        assert build_result.success is True

        sql = build_result.data["sql"]
        params = build_result.data["params"]

        guard_result = await tools.guard_sql(sql=sql)
        assert guard_result.success is True
        assert guard_result.data["passed"] is True

        execute_result = await tools.execute_readonly_sql(
            sql=sql,
            params=params,
            max_rows=20,
        )
        assert execute_result.success is True

        query_result = execute_result.data["query_result"]
        assert query_result["row_count"] == 1
        assert "gmv" in query_result["columns"]


@pytest.mark.anyio
async def test_bi_tools_conversion_rate_returns_data_source_missing() -> None:
    async with AsyncSessionLocal() as db:
        tools = BITools(db=db)

        result = await tools.build_metric_query(
            metric_key="conversion_rate",
            tenant_id=TENANT_ID,
            context={},
        )

        assert result.success is False
        assert result.error_code == "DATA_SOURCE_MISSING"
        assert "不能用订单数或用户数伪造转化率" in result.error_message


@pytest.mark.anyio
async def test_bi_tools_rejects_unsafe_sql_before_execution() -> None:
    async with AsyncSessionLocal() as db:
        tools = BITools(db=db)

        result = await tools.execute_readonly_sql(
            sql="SELECT * FROM order_info WHERE tenant_id = :tenant_id",
            params={"tenant_id": str(TENANT_ID)},
        )

        assert result.success is False
        assert result.error_code == "SQL_SELECT_STAR_FORBIDDEN"
