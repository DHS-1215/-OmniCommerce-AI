# -*- coding: utf-8 -*-
"""
创建时间    :2026/04/26 16:44
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient

from app.core.exceptions import (
    BaseAppException,
    NotFoundException,
    base_app_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.core.middleware import RequestContextMiddleware


def create_test_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(RequestContextMiddleware)
    app.add_exception_handler(BaseAppException, base_app_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    @app.get("/not-found")
    async def not_found():
        raise NotFoundException(message="item not found")

    @app.get("/unhandled")
    async def unhandled():
        raise RuntimeError("unexpected")

    return app


def test_base_app_exception_response_format():
    client = TestClient(create_test_app())

    response = client.get("/not-found")
    body = response.json()

    assert response.status_code == 404
    assert body["success"] is False
    assert body["code"] == "NOT_FOUND"
    assert body["message"] == "item not found"
    assert body["data"] is None
    assert body["request_id"].startswith("req_")


def test_unhandled_exception_response_format():
    client = TestClient(create_test_app(), raise_server_exceptions=False)

    response = client.get("/unhandled")
    body = response.json()

    assert response.status_code == 500
    assert body["success"] is False
    assert body["code"] == "INTERNAL_SERVER_ERROR"
    assert body["message"] == "Internal server error"
    assert body["data"] is None
    assert body["request_id"].startswith("req_")
