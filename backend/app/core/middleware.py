# -*- coding: utf-8 -*-
"""
创建时间    :2026/04/26 16:35
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    请求上下文中间件。

    职责：
    1. 为每个请求生成或透传 request_id
    2. 写入 request.state，供接口、异常处理、日志使用
    3. 写入响应头 X-Request-ID，方便前后端和日志排查问题
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID") or f"req_{uuid.uuid4().hex}"

        request.state.request_id = request_id
        request.state.tenant_id = None
        request.state.user_id = None

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        return response
