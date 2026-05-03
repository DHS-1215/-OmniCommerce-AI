# -*- coding: utf-8 -*-
"""
创建时间    :2026/04/26 16:38
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.core.middleware import RequestContextMiddleware
from app.core.response import success_response


def create_test_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(RequestContextMiddleware)

    @app.get("/ping")
    async def ping(request: Request):
        return success_response(
            data={"pong": True},
            request_id=request.state.request_id,
        )

    return app


def test_request_id_auto_generated():
    client = TestClient(create_test_app())

    response = client.get("/ping")

    assert response.status_code == 200
    body = response.json()

    assert body["success"] is True
    assert body["request_id"].startswith("req_")
    assert response.headers["X-Request-ID"] == body["request_id"]


def test_request_id_passthrough_from_header():
    client = TestClient(create_test_app())

    response = client.get("/ping", headers={"X-Request-ID": "req_test_123"})
    body = response.json()

    assert response.status_code == 200
    assert body["request_id"] == "req_test_123"
    assert response.headers["X-Request-ID"] == "req_test_123"
