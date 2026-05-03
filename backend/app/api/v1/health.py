# -*- coding: utf-8 -*-
"""
创建时间    :2026/04/26 17:14
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
# -*- coding: utf-8 -*-
import logging

import redis.asyncio as redis
from fastapi import APIRouter, Request
from sqlalchemy import text

from app.core.config import get_settings
from app.core.response import success_response
from app.db.session import AsyncSessionLocal

router = APIRouter(tags=["health"])
settings = get_settings()
logger = logging.getLogger(__name__)


async def check_database() -> str:
    """
    检查 PostgreSQL 连接状态。
    """

    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return "ok"
    except Exception as exc:
        logger.warning(
            "Database health check failed",
            extra={
                "module_name": "health",
                "event": "database_health_check_failed",
                "extra_data": {"error": str(exc)},
            },
        )
        return "error"


async def check_redis() -> str:
    """
    检查 Redis 连接状态。
    """

    client = redis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
    )

    try:
        await client.ping()
        return "ok"
    except Exception as exc:
        logger.warning(
            "Redis health check failed",
            extra={
                "module_name": "health",
                "event": "redis_health_check_failed",
                "extra_data": {"error": str(exc)},
            },
        )
        return "error"
    finally:
        await client.aclose()


@router.get("/health")
async def health(request: Request):
    """
    系统健康检查。

    验证：
    1. 后端服务状态
    2. PostgreSQL 连接状态
    3. Redis 连接状态
    """

    database_status = await check_database()
    redis_status = await check_redis()

    overall_status = (
        "ok"
        if database_status == "ok" and redis_status == "ok"
        else "degraded"
    )

    return success_response(
        data={
            "status": overall_status,
            "database": database_status,
            "redis": redis_status,
            "app": settings.app_name,
            "env": settings.app_env,
        },
        request_id=request.state.request_id,
    )