# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/05/04 15:34
IDE       :PyCharm
作者      :董宏升

执行窗口 11：评测中心数据访问层。
只负责 evaluation_case / evaluation_result 的数据库读写。
不调用 RAG，不调用 Agent，不计算指标，不提交事务。
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evaluation import EvaluationCase, EvaluationResult


class EvaluationRepository:
    """评测中心 Repository。"""

    async def create_case(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            case_no: str,
            case_type: str,
            name: str,
            description: str | None = None,
            input_json: dict[str, Any] | None = None,
            expected_output_json: dict[str, Any] | None = None,
            reference_context_json: list[Any] | None = None,
            tags_json: list[Any] | None = None,
            metadata_json: dict[str, Any] | None = None,
            status: str = "active",
    ) -> EvaluationCase:
        """创建评测用例。"""

        case = EvaluationCase(
            tenant_id=tenant_id,
            case_no=case_no,
            case_type=case_type,
            name=name,
            description=description,
            input_json=input_json or {},
            expected_output_json=expected_output_json,
            reference_context_json=reference_context_json,
            tags_json=tags_json,
            metadata_json=metadata_json,
            status=status,
        )
        db.add(case)
        await db.flush()
        await db.refresh(case)
        return case

    async def list_cases(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            page: int,
            page_size: int,
            case_type: str | None = None,
            status: str | None = None,
            keyword: str | None = None,
    ) -> tuple[list[EvaluationCase], int]:
        """分页查询评测用例。"""

        conditions = [
            EvaluationCase.tenant_id == tenant_id,
            EvaluationCase.deleted_at.is_(None),
        ]

        if case_type:
            conditions.append(EvaluationCase.case_type == case_type)

        if status:
            conditions.append(EvaluationCase.status == status)

        if keyword:
            like_keyword = f"%{keyword}%"
            conditions.append(
                EvaluationCase.name.ilike(like_keyword)
                | EvaluationCase.case_no.ilike(like_keyword)
            )

        count_stmt = select(func.count()).select_from(EvaluationCase).where(*conditions)
        total = int(await db.scalar(count_stmt) or 0)

        stmt = (
            select(EvaluationCase)
            .where(*conditions)
            .order_by(EvaluationCase.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all()), total

    async def list_active_cases_by_type(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            case_type: str,
    ) -> list[EvaluationCase]:
        """查询某类 active 评测用例。"""

        stmt = (
            select(EvaluationCase)
            .where(EvaluationCase.tenant_id == tenant_id)
            .where(EvaluationCase.case_type == case_type)
            .where(EvaluationCase.status == "active")
            .where(EvaluationCase.deleted_at.is_(None))
            .order_by(EvaluationCase.created_at.asc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def list_cases_by_ids(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            case_ids: list[UUID],
    ) -> list[EvaluationCase]:
        """按 ID 批量查询评测用例。"""

        if not case_ids:
            return []

        stmt = (
            select(EvaluationCase)
            .where(EvaluationCase.tenant_id == tenant_id)
            .where(EvaluationCase.id.in_(case_ids))
            .where(EvaluationCase.deleted_at.is_(None))
            .order_by(EvaluationCase.created_at.asc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_case_by_id(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            case_id: UUID,
    ) -> EvaluationCase | None:
        """根据 ID 查询评测用例。"""

        stmt = (
            select(EvaluationCase)
            .where(EvaluationCase.tenant_id == tenant_id)
            .where(EvaluationCase.id == case_id)
            .where(EvaluationCase.deleted_at.is_(None))
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_case(
            self,
            db: AsyncSession,
            *,
            case: EvaluationCase,
            values: dict[str, Any],
    ) -> EvaluationCase:
        """更新评测用例。"""

        for field_name, value in values.items():
            if hasattr(case, field_name):
                setattr(case, field_name, value)

        await db.flush()
        await db.refresh(case)
        return case

    async def archive_case(
            self,
            db: AsyncSession,
            *,
            case: EvaluationCase,
    ) -> EvaluationCase:
        """软归档评测用例。"""

        case.status = "archived"
        case.deleted_at = datetime.utcnow()

        await db.flush()
        await db.refresh(case)
        return case

    async def create_result(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            case_id: UUID,
            target_type: str,
            target_id: str | None,
            run_no: str | None,
            request_id: str | None,
            status: str,
            score: Decimal | None = None,
            answer_relevance: Decimal | None = None,
            faithfulness: Decimal | None = None,
            context_recall: Decimal | None = None,
            context_precision: Decimal | None = None,
            tool_call_success_rate: Decimal | None = None,
            agent_task_success_rate: Decimal | None = None,
            latency_ms: int | None = None,
            token_cost: Decimal | None = None,
            input_summary: str | None = None,
            output_summary: str | None = None,
            error_message: str | None = None,
            metrics_json: dict[str, Any] | None = None,
            metadata_json: dict[str, Any] | None = None,
    ) -> EvaluationResult:
        """创建评测结果。"""

        result = EvaluationResult(
            tenant_id=tenant_id,
            request_id=request_id,
            case_id=case_id,
            run_no=run_no,
            target_type=target_type,
            target_id=target_id,
            status=status,
            score=score,
            answer_relevance=answer_relevance,
            faithfulness=faithfulness,
            context_recall=context_recall,
            context_precision=context_precision,
            tool_call_success_rate=tool_call_success_rate,
            agent_task_success_rate=agent_task_success_rate,
            latency_ms=latency_ms,
            token_cost=token_cost,
            input_summary=input_summary,
            output_summary=output_summary,
            error_message=error_message,
            metrics_json=metrics_json,
            metadata_json=metadata_json,
        )
        db.add(result)
        await db.flush()
        await db.refresh(result)
        return result

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
            status: str | None = None,
    ) -> tuple[list[EvaluationResult], int]:
        """分页查询评测结果。"""

        conditions = [EvaluationResult.tenant_id == tenant_id]

        if run_no:
            conditions.append(EvaluationResult.run_no == run_no)

        if target_type:
            conditions.append(EvaluationResult.target_type == target_type)

        if target_id:
            conditions.append(EvaluationResult.target_id == target_id)

        if case_id:
            conditions.append(EvaluationResult.case_id == case_id)

        if status:
            conditions.append(EvaluationResult.status == status)

        count_stmt = select(func.count()).select_from(EvaluationResult).where(*conditions)
        total = int(await db.scalar(count_stmt) or 0)

        stmt = (
            select(EvaluationResult)
            .where(*conditions)
            .order_by(EvaluationResult.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all()), total

    async def list_results_for_report(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            run_no: str | None = None,
            target_type: str | None = None,
            limit: int = 100,
    ) -> list[EvaluationResult]:
        """查询评测报告需要的结果明细。"""

        conditions = [EvaluationResult.tenant_id == tenant_id]

        if run_no:
            conditions.append(EvaluationResult.run_no == run_no)

        if target_type:
            conditions.append(EvaluationResult.target_type == target_type)

        stmt = (
            select(EvaluationResult)
            .where(*conditions)
            .order_by(EvaluationResult.created_at.desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_report_summary(
            self,
            db: AsyncSession,
            *,
            tenant_id: UUID,
            run_no: str | None = None,
            target_type: str | None = None,
    ) -> dict[str, Any]:
        """聚合评测报告摘要。"""

        conditions = [EvaluationResult.tenant_id == tenant_id]

        if run_no:
            conditions.append(EvaluationResult.run_no == run_no)

        if target_type:
            conditions.append(EvaluationResult.target_type == target_type)

        stmt = select(
            func.count(EvaluationResult.id).label("total"),
            func.sum(case((EvaluationResult.status == "success", 1), else_=0)).label("success_count"),
            func.sum(case((EvaluationResult.status == "failed", 1), else_=0)).label("failed_count"),
            func.avg(EvaluationResult.score).label("avg_score"),
            func.avg(EvaluationResult.answer_relevance).label("avg_answer_relevance"),
            func.avg(EvaluationResult.faithfulness).label("avg_faithfulness"),
            func.avg(EvaluationResult.context_recall).label("avg_context_recall"),
            func.avg(EvaluationResult.context_precision).label("avg_context_precision"),
            func.avg(EvaluationResult.tool_call_success_rate).label("avg_tool_call_success_rate"),
            func.avg(EvaluationResult.agent_task_success_rate).label("avg_agent_task_success_rate"),
        ).where(*conditions)

        row = (await db.execute(stmt)).mappings().one()

        return {
            "total": int(row["total"] or 0),
            "success_count": int(row["success_count"] or 0),
            "failed_count": int(row["failed_count"] or 0),
            "avg_score": row["avg_score"],
            "avg_answer_relevance": row["avg_answer_relevance"],
            "avg_faithfulness": row["avg_faithfulness"],
            "avg_context_recall": row["avg_context_recall"],
            "avg_context_precision": row["avg_context_precision"],
            "avg_tool_call_success_rate": row["avg_tool_call_success_rate"],
            "avg_agent_task_success_rate": row["avg_agent_task_success_rate"],
        }

