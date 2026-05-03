# -*- coding: utf-8 -*-
"""
FastAPI 应用入口。

执行窗口 1 只负责基础工程骨架：
- 应用初始化
- 路由挂载
- 配置系统接入
- 统一响应格式接入
- request_id 请求追踪接入
- 统一异常处理接入
- 结构化日志接入

禁止在本文件中实现商品、订单、Agent、RAG、Prompt、模型网关等后续业务逻辑。
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError

from app.api.v1.router import api_v1_router
from app.core.config import get_settings
from app.core.exceptions import (
    BaseAppException,
    base_app_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.core.logging import setup_logging
from app.core.middleware import RequestContextMiddleware
from app.core.response import success_response

settings = get_settings()
setup_logging(settings.log_level)

logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    debug=False,
)

app.add_middleware(RequestContextMiddleware)

app.add_exception_handler(BaseAppException, base_app_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

app.include_router(api_v1_router, prefix="/api/v1")


@app.get("/")
async def root(request: Request):
    logger.info(
        "Root endpoint called",
        extra={
            "module_name": "core",
            "event": "root_called",
            "request_id": request.state.request_id,
        },
    )

    return success_response(
        data={
            "app": settings.app_name,
            "env": settings.app_env,
            "status": "running",
        },
        request_id=request.state.request_id,
    )