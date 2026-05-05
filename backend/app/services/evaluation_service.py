# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/05/04 15:40
IDE       :PyCharm
作者      :董宏升

执行窗口 11：评测中心业务服务。
职责：
- 评测用例管理；
- RAG / Agent 评测执行；
- 评测结果写入 evaluation_result；
- Prompt 版本与检索策略结果对比；
- 评测报告聚合。
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.core.exceptions import BaseAppException
from app.evaluations.agent_eval import AgentEvaluator
from app.evaluations.metrics import flatten_text
from app.evaluations.rag_eval import RagEvaluator
from app.repositories.evaluation_repository import EvaluationRepository
from app.schemas.common import PageResponse
from app.schemas.evaluation import (
    AgentEvaluationRunRequest,
    EvaluationCaseCreate,
    EvaluationCaseResponse,
    EvaluationCaseUpdate,
    EvaluationReportResponse,
    EvaluationResultResponse,
    EvaluationRunResponse,
    PromptCompareRequest,
    RagEvaluationRunRequest,
    RetrievalCompareRequest,
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _new_run_no(prefix: str) -> str:
    return f"{prefix.upper()}-{_utc_now().strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:6].upper()}"


def _truncate(value: Any, max_length: int = 800) -> str | None:
    text = flatten_text(value)
    if not text:
        return None
    return text if len(text) <= max_length else text[:max_length] + "...[truncated]"


def _decimal_to_float(value: Decimal | None) -> float | None:
    return float(value) if value is not None else None


class EvaluationService:
    """评测中心业务服务。"""

    def __init__(self) -> None:
        self.repository = EvaluationRepository()
        self.rag_evaluator = RagEvaluator()
        self.agent_evaluator = AgentEvaluator()

    async def create_case(
            self,
            db: AsyncSession,
            *,
            payload: EvaluationCaseCreate,
    ) -> EvaluationCaseResponse:
        """创建评测用例。"""

        try:
            item = await self.repository.create_case(
                db,
                tenant_id=payload.tenant_id,
                case_no=payload.case_no,
                case_type=payload.case_type,
                name=payload.name,
                description=payload.description,
                input_json=payload.input_json,
                expected_output_json=payload.expected_output_json,
                reference_context_json=payload.reference_context_json,
                tags_json=payload.tags_json,
                metadata_json=payload.metadata_json,
                status=payload.status,
            )
            await db.commit()
            await db.refresh(item)
        except IntegrityError as exc:
            await db.rollback()
            raise BaseAppException(
                code="EVALUATION_CASE_CONFLICT",
                message="评测用例编号已存在或违反唯一约束",
                status_code=status.HTTP_409_CONFLICT,
                data={"case_no": payload.case_no},
            ) from exc
        except Exception:
            await db.rollback()
            raise

        return EvaluationCaseResponse.model_validate(item)

    async def list_cases(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            page: int,
            page_size: int,
            case_type: str | None = None,
            status_filter: str | None = None,
            keyword: str | None = None,
    ) -> PageResponse[EvaluationCaseResponse]:
        """分页查询评测用例。"""

        items, total = await self.repository.list_cases(
            db,
            tenant_id=tenant_id,
            page=page,
            page_size=page_size,
            case_type=case_type,
            status=status_filter,
            keyword=keyword,
        )
        return PageResponse[EvaluationCaseResponse](
            items=[EvaluationCaseResponse.model_validate(item) for item in items],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def get_case(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            case_id: UUID,
    ) -> EvaluationCaseResponse:
        """查询评测用例详情。"""

        item = await self.repository.get_case_by_id(
            db,
            tenant_id=tenant_id,
            case_id=case_id,
        )
        if item is None:
            raise BaseAppException(
                code="EVALUATION_CASE_NOT_FOUND",
                message="评测用例不存在",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        return EvaluationCaseResponse.model_validate(item)

    async def update_case(
            self,
            db: AsyncSession,
            *,
            case_id: UUID,
            payload: EvaluationCaseUpdate,
    ) -> EvaluationCaseResponse:
        """更新评测用例。"""

        item = await self.repository.get_case_by_id(
            db,
            tenant_id=payload.tenant_id,
            case_id=case_id,
        )
        if item is None:
            raise BaseAppException(
                code="EVALUATION_CASE_NOT_FOUND",
                message="评测用例不存在",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        values = payload.model_dump(
            exclude={"tenant_id"},
            exclude_unset=True,
        )
        if not values:
            return EvaluationCaseResponse.model_validate(item)

        try:
            item = await self.repository.update_case(
                db,
                case=item,
                values=values,
            )
            await db.commit()
            await db.refresh(item)
        except Exception:
            await db.rollback()
            raise

        return EvaluationCaseResponse.model_validate(item)

    async def archive_case(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            case_id: UUID,
    ) -> EvaluationCaseResponse:
        """归档评测用例。"""

        item = await self.repository.get_case_by_id(
            db,
            tenant_id=tenant_id,
            case_id=case_id,
        )
        if item is None:
            raise BaseAppException(
                code="EVALUATION_CASE_NOT_FOUND",
                message="评测用例不存在",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        try:
            item = await self.repository.archive_case(db, case=item)
            await db.commit()
            await db.refresh(item)
        except Exception:
            await db.rollback()
            raise

        return EvaluationCaseResponse.model_validate(item)

    async def run_rag_evaluation(
            self,
            db: AsyncSession,
            *,
            payload: RagEvaluationRunRequest,
            request_id: str | None = None,
    ) -> EvaluationRunResponse:
        """执行 RAG 评测。"""

        cases = await self._load_cases(
            db,
            tenant_id=payload.tenant_id,
            case_ids=payload.case_ids,
            case_type="rag",
        )

        if not cases:
            raise BaseAppException(
                code="EVALUATION_CASE_EMPTY",
                message="没有可执行的 RAG 评测用例",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        run_no = payload.run_no or _new_run_no("rag")
        results = []
        success_count = 0
        failed_count = 0

        for case in cases:
            response_data = None
            metric_values: dict[str, Any] = {}
            latency_ms = 0
            error_message = None

            try:
                response_data, metric_values, latency_ms, error_message = (
                    await self.rag_evaluator.run_case(
                        db,
                        case=case,
                        tenant_id=payload.tenant_id,
                        top_k=payload.top_k,
                        request_id=request_id,
                    )
                )
                status_value = "failed" if error_message else "success"
            except Exception as exc:  # noqa: BLE001
                await db.rollback()
                status_value = "failed"
                error_message = str(exc)

            try:
                result = await self.repository.create_result(
                    db,
                    tenant_id=payload.tenant_id,
                    case_id=case.id,
                    target_type="rag",
                    target_id=payload.target_id or "knowledge_ask",
                    run_no=run_no,
                    request_id=request_id,
                    status=status_value,
                    score=metric_values.get("score"),
                    answer_relevance=metric_values.get("answer_relevance"),
                    faithfulness=metric_values.get("faithfulness"),
                    context_recall=metric_values.get("context_recall"),
                    context_precision=metric_values.get("context_precision"),
                    latency_ms=latency_ms,
                    input_summary=_truncate(case.input_json),
                    output_summary=_truncate(response_data),
                    error_message=error_message,
                    metrics_json=metric_values.get("metrics_json"),
                    metadata_json={
                        "case_no": case.case_no,
                        "case_type": case.case_type,
                        "runner": "RagEvaluator",
                        **(payload.metadata_json or {}),
                    },
                )
                await db.commit()
                await db.refresh(result)
            except Exception:
                await db.rollback()
                raise

            if status_value == "success":
                success_count += 1
            else:
                failed_count += 1

            results.append(EvaluationResultResponse.model_validate(result))

        return EvaluationRunResponse(
            run_no=run_no,
            target_type="rag",
            total=len(results),
            success_count=success_count,
            failed_count=failed_count,
            results=results,
        )

    async def run_agent_evaluation(
            self,
            db: AsyncSession,
            *,
            payload: AgentEvaluationRunRequest,
            request_id: str | None = None,
    ) -> EvaluationRunResponse:
        """执行 Agent 评测。"""

        case_type = self._agent_case_type(payload.agent_type)
        cases = await self._load_cases(
            db,
            tenant_id=payload.tenant_id,
            case_ids=payload.case_ids,
            case_type=case_type,
        )

        if not cases and payload.case_ids is None:
            cases = await self.repository.list_active_cases_by_type(
                db,
                tenant_id=payload.tenant_id,
                case_type="agent",
            )

        if not cases:
            raise BaseAppException(
                code="EVALUATION_CASE_EMPTY",
                message="没有可执行的 Agent 评测用例",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        run_no = payload.run_no or _new_run_no(payload.agent_type)
        target_type = case_type
        results = []
        success_count = 0
        failed_count = 0

        for case in cases:
            response_data = None
            metric_values: dict[str, Any] = {}
            latency_ms = 0
            error_message = None

            try:
                response_data, metric_values, latency_ms, error_message = (
                    await self.agent_evaluator.run_case(
                        db,
                        case=case,
                        tenant_id=payload.tenant_id,
                        agent_type=payload.agent_type,
                        request_id=request_id,
                    )
                )
                status_value = "failed" if error_message else "success"
            except Exception as exc:  # noqa: BLE001
                await db.rollback()
                status_value = "failed"
                error_message = str(exc)

            try:
                result = await self.repository.create_result(
                    db,
                    tenant_id=payload.tenant_id,
                    case_id=case.id,
                    target_type=target_type,
                    target_id=payload.target_id or payload.agent_type,
                    run_no=run_no,
                    request_id=request_id,
                    status=status_value,
                    score=metric_values.get("score"),
                    answer_relevance=metric_values.get("answer_relevance"),
                    faithfulness=metric_values.get("faithfulness"),
                    context_recall=metric_values.get("context_recall"),
                    context_precision=metric_values.get("context_precision"),
                    tool_call_success_rate=metric_values.get("tool_call_success_rate"),
                    agent_task_success_rate=metric_values.get("agent_task_success_rate"),
                    latency_ms=latency_ms,
                    input_summary=_truncate(case.input_json),
                    output_summary=_truncate(response_data),
                    error_message=error_message,
                    metrics_json=metric_values.get("metrics_json"),
                    metadata_json={
                        "case_no": case.case_no,
                        "case_type": case.case_type,
                        "agent_type": payload.agent_type,
                        "runner": "AgentEvaluator",
                        **(payload.metadata_json or {}),
                    },
                )
                await db.commit()
                await db.refresh(result)
            except Exception:
                await db.rollback()
                raise

            if status_value == "success":
                success_count += 1
            else:
                failed_count += 1

            results.append(EvaluationResultResponse.model_validate(result))

        return EvaluationRunResponse(
            run_no=run_no,
            target_type=target_type,
            total=len(results),
            success_count=success_count,
            failed_count=failed_count,
            results=results,
        )

    async def list_results(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            page: int,
            page_size: int,
            run_no: str | None = None,
            target_type: str | None = None,
            target_id: str | None = None,
            case_id: UUID | None = None,
            status_filter: str | None = None,
    ) -> PageResponse[EvaluationResultResponse]:
        """分页查询评测结果。"""

        items, total = await self.repository.list_results(
            db,
            tenant_id=tenant_id,
            page=page,
            page_size=page_size,
            run_no=run_no,
            target_type=target_type,
            target_id=target_id,
            case_id=case_id,
            status=status_filter,
        )
        return PageResponse[EvaluationResultResponse](
            items=[EvaluationResultResponse.model_validate(item) for item in items],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def get_report(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            run_no: str | None = None,
            target_type: str | None = None,
    ) -> EvaluationReportResponse:
        """查询评测报告。"""

        summary = await self.repository.get_report_summary(
            db,
            tenant_id=tenant_id,
            run_no=run_no,
            target_type=target_type,
        )
        items = await self.repository.list_results_for_report(
            db,
            tenant_id=tenant_id,
            run_no=run_no,
            target_type=target_type,
            limit=100,
        )

        return EvaluationReportResponse(
            tenant_id=tenant_id,
            run_no=run_no,
            target_type=target_type,
            total=summary["total"],
            success_count=summary["success_count"],
            failed_count=summary["failed_count"],
            avg_score=summary["avg_score"],
            avg_answer_relevance=summary["avg_answer_relevance"],
            avg_faithfulness=summary["avg_faithfulness"],
            avg_context_recall=summary["avg_context_recall"],
            avg_context_precision=summary["avg_context_precision"],
            avg_tool_call_success_rate=summary["avg_tool_call_success_rate"],
            avg_agent_task_success_rate=summary["avg_agent_task_success_rate"],
            items=[EvaluationResultResponse.model_validate(item) for item in items],
        )

    async def compare_prompt_versions(
            self,
            db: AsyncSession,
            *,
            payload: PromptCompareRequest,
    ) -> dict[str, Any]:
        """
        对比 Prompt 版本。

        第一版不绕过 PromptService 重跑模型，而是对已入库 evaluation_result 做聚合对比。
        target_type = prompt，target_id = prompt_version_id。
        """

        return await self._compare_target_ids(
            db,
            tenant_id=payload.tenant_id,
            target_type="prompt",
            target_ids=[str(item) for item in payload.prompt_version_ids],
            run_no=payload.run_no,
            metadata_json=payload.metadata_json,
        )

    async def compare_retrieval_strategies(
            self,
            db: AsyncSession,
            *,
            payload: RetrievalCompareRequest,
    ) -> dict[str, Any]:
        """
        对比检索策略。

        第一版使用 strategy_id 作为 target_id 查询已入库 RAG 评测结果。
        如果调用方没有传 strategy_id，则使用 strategy_1 / strategy_2 ...
        """

        target_ids = []
        strategy_map = {}

        for index, strategy in enumerate(payload.strategies, start=1):
            strategy_id = str(strategy.get("strategy_id") or f"strategy_{index}")
            target_ids.append(strategy_id)
            strategy_map[strategy_id] = strategy

        result = await self._compare_target_ids(
            db,
            tenant_id=payload.tenant_id,
            target_type="rag",
            target_ids=target_ids,
            run_no=payload.run_no,
            metadata_json=payload.metadata_json,
        )
        result["strategies"] = strategy_map
        return result

    async def _compare_target_ids(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            target_type: str,
            target_ids: list[str],
            run_no: str | None,
            metadata_json: dict[str, Any] | None,
    ) -> dict[str, Any]:
        comparisons = []

        for target_id in target_ids:
            report = await self.get_report(
                db,
                tenant_id=tenant_id,
                run_no=run_no,
                target_type=target_type,
            )
            filtered_items = [
                item
                for item in report.items
                if item.target_id == target_id
            ]
            scores = [
                _decimal_to_float(item.score)
                for item in filtered_items
                if item.score is not None
            ]

            comparisons.append(
                {
                    "target_id": target_id,
                    "target_type": target_type,
                    "total": len(filtered_items),
                    "avg_score": (
                        sum(scores) / len(scores)
                        if scores
                        else None
                    ),
                    "success_count": sum(
                        1 for item in filtered_items if item.status == "success"
                    ),
                    "failed_count": sum(
                        1 for item in filtered_items if item.status == "failed"
                    ),
                }
            )

        comparisons.sort(
            key=lambda item: item["avg_score"] if item["avg_score"] is not None else -1,
            reverse=True,
        )

        return {
            "tenant_id": str(tenant_id),
            "target_type": target_type,
            "run_no": run_no,
            "items": comparisons,
            "best_target_id": comparisons[0]["target_id"] if comparisons else None,
            "metadata_json": metadata_json or {},
        }

    async def _load_cases(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            case_ids: list[UUID] | None,
            case_type: str,
    ):
        if case_ids:
            return await self.repository.list_cases_by_ids(
                db,
                tenant_id=tenant_id,
                case_ids=case_ids,
            )

        return await self.repository.list_active_cases_by_type(
            db,
            tenant_id=tenant_id,
            case_type=case_type,
        )

    @staticmethod
    def _agent_case_type(agent_type: str) -> str:
        if agent_type == "customer_service":
            return "customer_service_agent"
        if agent_type == "shopping_guide":
            return "shopping_guide_agent"
        if agent_type == "operation_copilot":
            return "operation_copilot_agent"
        return "agent"
