# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/05/01 21:13
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class KnowledgeDocumentResponse(BaseModel):
    """
    知识库文档响应结构。
    """

    id: UUID
    tenant_id: UUID
    document_no: str
    title: str
    source_type: str
    source_uri: str | None = None
    storage_object_key: str | None = None
    mime_type: str | None = None
    file_size: int | None = None
    language: str | None = None
    content_hash: str | None = None
    status: str
    parser_status: str
    acl_json: dict[str, Any] | None = None
    metadata_json: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True,
    }


class KnowledgeChunkResponse(BaseModel):
    """
    知识库切片响应结构。
    """

    id: UUID
    tenant_id: UUID
    document_id: UUID
    chunk_no: str
    content: str
    page_no: int | None = None
    section_title: str | None = None
    keywords_json: list[str] | dict[str, Any] | None = None
    token_count: int | None = None
    embedding_id: str | None = None
    vector_collection: str | None = None
    metadata_json: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True,
    }


class KnowledgeDocumentUploadResponse(BaseModel):
    """
    文档上传并入库后的响应。
    """

    document: KnowledgeDocumentResponse
    chunk_count: int


class KnowledgeDocumentListResponse(BaseModel):
    """
    文档分页列表响应。
    """

    items: list[KnowledgeDocumentResponse]
    total: int
    page: int
    page_size: int


class KnowledgeSearchRequest(BaseModel):
    """
    知识库检索请求。
    """

    tenant_id: UUID
    query: str = Field(min_length=1, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=20)


class KnowledgeSearchHit(BaseModel):
    """
    知识库检索命中的切片。
    """

    document_id: UUID
    document_title: str
    chunk_id: UUID
    chunk_no: str
    page_no: int | None = None
    section_title: str | None = None
    score: float
    vector_score: float = 0.0
    keyword_score: float = 0.0
    content_snippet: str
    metadata_json: dict[str, Any] | None = None


class KnowledgeSearchResponse(BaseModel):
    """
    知识库检索响应。
    """

    query: str
    items: list[KnowledgeSearchHit]


class KnowledgeAskRequest(BaseModel):
    """
    RAG 问答请求。
    """

    tenant_id: UUID
    question: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)


class KnowledgeCitation(BaseModel):
    """
    RAG 回答引用来源。
    """

    document_id: UUID
    document_title: str
    chunk_id: UUID
    chunk_no: str
    page_no: int | None = None
    section_title: str | None = None
    score: float
    content_snippet: str


class KnowledgeAskResponse(BaseModel):
    """
    RAG 问答响应。
    """

    question: str
    answer: str
    citations: list[KnowledgeCitation]
    prompt_template_id: UUID | None = None
    prompt_version_id: UUID | None = None