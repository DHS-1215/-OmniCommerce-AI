# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/28 18:33
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
import uuid

import httpx
import pytest

from app.db.session import get_db_session
from app.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


class FakeDbSession:
    def add(self, instance):
        self.instance = instance

    async def commit(self):
        return None

    async def refresh(self, instance):
        return None

    async def rollback(self):
        return None


async def override_get_db_session():
    yield FakeDbSession()


@pytest.fixture(autouse=True)
def override_dependencies():
    app.dependency_overrides[get_db_session] = override_get_db_session
    yield
    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_llm_chat_api_should_return_unified_response_and_request_id():
    tenant_id = str(uuid.uuid4())

    async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
    ) as client:
        response = await client.post(
            "/api/v1/llm/chat",
            json={
                "tenant_id": tenant_id,
                "provider": "mock",
                "model": "mock-chat-model",
                "messages": [
                    {
                        "role": "user",
                        "content": "你好",
                    }
                ],
            },
        )

    assert response.status_code == 200

    body = response.json()
    assert body["success"] is True
    assert body["code"] == "OK"
    assert body["message"] == "success"
    assert body["request_id"] is not None
    assert body["data"]["provider"] == "mock"
    assert body["data"]["model_name"] == "mock-chat-model"
    assert body["data"]["content"] == "[mock] 你好"


@pytest.mark.anyio
async def test_llm_embeddings_api_should_return_unified_response_and_request_id():
    tenant_id = str(uuid.uuid4())

    async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
    ) as client:
        response = await client.post(
            "/api/v1/llm/embeddings",
            json={
                "tenant_id": tenant_id,
                "provider": "mock",
                "model": "mock-embedding-model",
                "texts": [
                    "智能客服",
                    "企业知识库 RAG",
                ],
            },
        )

    assert response.status_code == 200

    body = response.json()
    assert body["success"] is True
    assert body["code"] == "OK"
    assert body["message"] == "success"
    assert body["request_id"] is not None
    assert body["data"]["provider"] == "mock"
    assert body["data"]["model_name"] == "mock-embedding-model"
    assert len(body["data"]["embeddings"]) == 2
    assert len(body["data"]["embeddings"][0]) == 3


@pytest.mark.anyio
async def test_llm_stream_api_should_return_sse_and_request_id_header():
    tenant_id = str(uuid.uuid4())

    async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
    ) as client:
        response = await client.post(
            "/api/v1/llm/chat/stream",
            json={
                "tenant_id": tenant_id,
                "provider": "mock",
                "model": "mock-chat-model",
                "messages": [
                    {
                        "role": "user",
                        "content": "请流式输出",
                    }
                ],
            },
        )

    assert response.status_code == 200
    assert response.headers.get("x-request-id") is not None
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "data:" in response.text
    assert "[DONE]" in response.text
