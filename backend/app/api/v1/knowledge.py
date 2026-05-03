# -*- coding: utf-8 -*-
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.helpers import get_request_id, to_response_data
from app.core.response import ApiResponse, success_response
from app.db.session import get_db_session
from app.schemas.knowledge import KnowledgeAskRequest, KnowledgeSearchRequest
from app.services.knowledge_service import KnowledgeService

router = APIRouter()

knowledge_service = KnowledgeService()


@router.post(
    "/documents/upload",
    response_model=ApiResponse,
    summary="上传知识库文档并完成 RAG 入库",
)
async def upload_knowledge_document(
        request: Request,
        tenant_id: UUID = Form(..., description="租户 ID"),
        file: UploadFile = File(..., description="上传文档文件"),
        title: str | None = Form(default=None, description="文档标题，不传则使用文件名"),
        language: str | None = Form(default="zh-CN", description="文档语言"),
        user_id: UUID | None = Form(default=None, description="用户 ID，认证模块完成前显式传入"),
        db: AsyncSession = Depends(get_db_session),
) -> ApiResponse:
    """
    上传知识库文档。

    当前支持：
    - .txt
    - .md / .markdown
    - .pdf
    - .docx
    - .xlsx
    - .pptx
    - .png / .jpg / .jpeg OCR
    - 扫描版 PDF OCR

    入库主链路：
    上传 -> ParserRegistry -> 解析 -> 切片 -> Embedding -> Qdrant -> PostgreSQL 元数据。
    """

    data = await knowledge_service.upload_document(
        db,
        tenant_id=tenant_id,
        file=file,
        title=title,
        language=language,
        acl_json={},
        request_id=get_request_id(request),
        user_id=user_id,
    )

    return success_response(
        data=to_response_data(data),
        request_id=get_request_id(request),
    )


@router.get(
    "/documents",
    response_model=ApiResponse,
    summary="查询知识库文档列表",
)
async def list_knowledge_documents(
        request: Request,
        tenant_id: UUID = Query(..., description="租户 ID"),
        page: int = Query(default=1, ge=1, description="页码"),
        page_size: int = Query(default=20, ge=1, le=100, description="每页数量"),
        status: str | None = Query(default=None, description="文档状态"),
        keyword: str | None = Query(default=None, description="文档标题关键词"),
        db: AsyncSession = Depends(get_db_session),
) -> ApiResponse:
    """
    查询知识库文档列表。
    """

    data = await knowledge_service.list_documents(
        db,
        tenant_id=tenant_id,
        page=page,
        page_size=page_size,
        status_filter=status,
        keyword=keyword,
    )

    return success_response(
        data=to_response_data(data),
        request_id=get_request_id(request),
    )


@router.post(
    "/search",
    response_model=ApiResponse,
    summary="知识库混合检索",
)
async def search_knowledge(
        request: Request,
        payload: KnowledgeSearchRequest,
        user_id: UUID | None = Query(default=None, description="用户 ID，认证模块完成前显式传入"),
        db: AsyncSession = Depends(get_db_session),
) -> ApiResponse:
    """
    知识库混合检索。

    当前检索策略：
    - Qdrant 向量检索
    - SimpleKeywordStore 轻量关键词检索
    - HybridRetriever 加权融合
    - NoopReranker 占位排序
    """

    data = await knowledge_service.search(
        db,
        tenant_id=payload.tenant_id,
        query=payload.query,
        top_k=payload.top_k,
        request_id=get_request_id(request),
        user_id=user_id,
    )

    return success_response(
        data=to_response_data(data),
        request_id=get_request_id(request),
    )


@router.post(
    "/ask",
    response_model=ApiResponse,
    summary="知识库 RAG 问答",
)
async def ask_knowledge(
        request: Request,
        payload: KnowledgeAskRequest,
        user_id: UUID | None = Query(default=None, description="用户 ID，认证模块完成前显式传入"),
        db: AsyncSession = Depends(get_db_session),
) -> ApiResponse:
    """
    知识库 RAG 问答。

    主链路：
    问题 -> 混合检索 -> NoopReranker -> 上下文组装 -> PromptService -> ModelGateway -> 引用溯源。
    """

    data = await knowledge_service.ask(
        db,
        tenant_id=payload.tenant_id,
        question=payload.question,
        top_k=payload.top_k,
        request_id=get_request_id(request),
        user_id=user_id,
    )

    return success_response(
        data=to_response_data(data),
        request_id=get_request_id(request),
    )