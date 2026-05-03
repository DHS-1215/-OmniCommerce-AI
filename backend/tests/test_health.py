# -*- coding: utf-8 -*-
"""
创建时间    :2026/04/26 19:01
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from fastapi.testclient import TestClient

from app.main import app


def test_health_response_format():
    client = TestClient(app)

    response = client.get("/api/v1/health")
    body = response.json()

    assert response.status_code == 200
    assert body["success"] is True
    assert body["code"] == "OK"
    assert body["message"] == "success"
    assert body["request_id"].startswith("req_")

    assert "status" in body["data"]
    assert "database" in body["data"]
    assert "redis" in body["data"]

    assert body["data"]["status"] in ["ok", "degraded"]
    assert body["data"]["database"] in ["ok", "error"]
    assert body["data"]["redis"] in ["ok", "error"]