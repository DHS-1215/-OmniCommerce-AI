# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/05/04 15:44
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_dependencies import CurrentUser, ensure_tenant_allowed, require_roles
from app.core.response import success_response
from app.db.session import get_db_session
from app.schemas.evaluation import (
    AgentEvaluationRunRequest,
    EvaluationCaseCreate,
    EvaluationCaseUpdate,
    PromptCompareRequest,
    RagEvaluationRunRequest,
    RetrievalCompareRequest,
)
from app.services.evaluation_service import EvaluationService

router = APIRouter()


@router.post("/cases")
async def create_evaluation_case(
        payload: EvaluationCaseCreate,
        request: Request,
        db: AsyncSession = Depends(get_db_session),
):
    """创建评测用例。"""

    service = EvaluationService()
    result = await service.create_case(
        db,
        payload=payload,
    )
    return success_response(
        data=result,
        request_id=getattr(request.state, "request_id", None),
    )


@router.get("/cases")
async def list_evaluation_cases(
        request: Request,
        tenant_id: UUID = Query(..., description="租户 ID"),
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=20, ge=1, le=100),
        case_type: str | None = Query(default=None),
        status_filter: str | None = Query(default=None, alias="status"),
        keyword: str | None = Query(default=None),
        db: AsyncSession = Depends(get_db_session),
):
    """查询评测用例列表。"""

    service = EvaluationService()
    result = await service.list_cases(
        db,
        tenant_id=tenant_id,
        page=page,
        page_size=page_size,
        case_type=case_type,
        status_filter=status_filter,
        keyword=keyword,
    )
    return success_response(
        data=result,
        request_id=getattr(request.state, "request_id", None),
    )


@router.get("/cases/{case_id}")
async def get_evaluation_case(
        case_id: UUID,
        request: Request,
        tenant_id: UUID = Query(..., description="租户 ID"),
        db: AsyncSession = Depends(get_db_session),
):
    """查询评测用例详情。"""

    service = EvaluationService()
    result = await service.get_case(
        db,
        tenant_id=tenant_id,
        case_id=case_id,
    )
    return success_response(
        data=result,
        request_id=getattr(request.state, "request_id", None),
    )


@router.patch("/cases/{case_id}")
async def update_evaluation_case(
        case_id: UUID,
        payload: EvaluationCaseUpdate,
        request: Request,
        db: AsyncSession = Depends(get_db_session),
):
    """更新评测用例。"""

    service = EvaluationService()
    result = await service.update_case(
        db,
        case_id=case_id,
        payload=payload,
    )
    return success_response(
        data=result,
        request_id=getattr(request.state, "request_id", None),
    )


@router.delete("/cases/{case_id}")
async def archive_evaluation_case(
        case_id: UUID,
        request: Request,
        tenant_id: UUID = Query(..., description="租户 ID"),
        db: AsyncSession = Depends(get_db_session),
):
    """归档评测用例。"""

    service = EvaluationService()
    result = await service.archive_case(
        db,
        tenant_id=tenant_id,
        case_id=case_id,
    )
    return success_response(
        data=result,
        request_id=getattr(request.state, "request_id", None),
    )


@router.post("/rag/run")
async def run_rag_evaluation(
        payload: RagEvaluationRunRequest,
        request: Request,
        db: AsyncSession = Depends(get_db_session),
        current_user: CurrentUser | None = Depends(require_roles("admin")),
):
    """执行 RAG 评测。"""

    request_id = getattr(request.state, "request_id", None)

    ensure_tenant_allowed(
        provided_tenant_id=getattr(payload, "tenant_id", None),
        current_user=current_user,
    )

    service = EvaluationService()
    result = await service.run_rag_evaluation(
        db,
        payload=payload,
        request_id=request_id,
    )
    return success_response(
        data=result,
        request_id=request_id,
    )


@router.post("/agents/run")
async def run_agent_evaluation(
        payload: AgentEvaluationRunRequest,
        request: Request,
        db: AsyncSession = Depends(get_db_session),
        current_user: CurrentUser | None = Depends(require_roles("admin")),
):
    """执行 Agent 评测。"""

    request_id = getattr(request.state, "request_id", None)

    ensure_tenant_allowed(
        provided_tenant_id=getattr(payload, "tenant_id", None),
        current_user=current_user,
    )

    service = EvaluationService()
    result = await service.run_agent_evaluation(
        db,
        payload=payload,
        request_id=request_id,
    )
    return success_response(
        data=result,
        request_id=request_id,
    )


@router.get("/results")
async def list_evaluation_results(
        request: Request,
        tenant_id: UUID = Query(..., description="租户 ID"),
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=20, ge=1, le=100),
        run_no: str | None = Query(default=None),
        target_type: str | None = Query(default=None),
        target_id: str | None = Query(default=None),
        case_id: UUID | None = Query(default=None),
        status_filter: str | None = Query(default=None, alias="status"),
        db: AsyncSession = Depends(get_db_session),
):
    """查询评测结果列表。"""

    service = EvaluationService()
    result = await service.list_results(
        db,
        tenant_id=tenant_id,
        page=page,
        page_size=page_size,
        run_no=run_no,
        target_type=target_type,
        target_id=target_id,
        case_id=case_id,
        status_filter=status_filter,
    )
    return success_response(
        data=result,
        request_id=getattr(request.state, "request_id", None),
    )


@router.get("/report")
async def get_evaluation_report(
        request: Request,
        tenant_id: UUID = Query(..., description="租户 ID"),
        run_no: str | None = Query(default=None),
        target_type: str | None = Query(default=None),
        db: AsyncSession = Depends(get_db_session),
):
    """查询评测报告。"""

    service = EvaluationService()
    result = await service.get_report(
        db,
        tenant_id=tenant_id,
        run_no=run_no,
        target_type=target_type,
    )
    return success_response(
        data=result,
        request_id=getattr(request.state, "request_id", None),
    )


@router.post("/compare/prompts")
async def compare_prompt_versions(
        payload: PromptCompareRequest,
        request: Request,
        db: AsyncSession = Depends(get_db_session),
):
    """对比 Prompt 版本评测结果。"""

    service = EvaluationService()
    result = await service.compare_prompt_versions(
        db,
        payload=payload,
    )
    return success_response(
        data=result,
        request_id=getattr(request.state, "request_id", None),
    )


@router.post("/compare/retrieval")
async def compare_retrieval_strategies(
        payload: RetrievalCompareRequest,
        request: Request,
        db: AsyncSession = Depends(get_db_session),
):
    """对比检索策略评测结果。"""

    service = EvaluationService()
    result = await service.compare_retrieval_strategies(
        db,
        payload=payload,
    )
    return success_response(
        data=result,
        request_id=getattr(request.state, "request_id", None),
    )
