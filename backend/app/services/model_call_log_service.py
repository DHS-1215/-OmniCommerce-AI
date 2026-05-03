# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/28 18:13
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.llm import ModelCallLog


class ModelCallLogService:
    """
    模型调用日志服务。

    仅负责 model_call_log 入库。
    不负责真实模型调用，不负责 Prompt 渲染，不负责 Agent / RAG。
    """

    def __init__(self, db_session: AsyncSession) -> None:
        self.db_session = db_session

    async def create_log(
            self,
            *,
            tenant_id: uuid.UUID,
            provider: str,
            model_name: str,
            model_type: str,
            call_type: str,
            status: str,
            request_id: str | None = None,
            user_id: uuid.UUID | None = None,
            prompt_template_id: uuid.UUID | None = None,
            prompt_version_id: uuid.UUID | None = None,
            input_tokens: int | None = None,
            output_tokens: int | None = None,
            total_tokens: int | None = None,
            cost_amount: Decimal | None = None,
            currency: str | None = None,
            latency_ms: int | None = None,
            error_code: str | None = None,
            error_message: str | None = None,
            input_summary: str | None = None,
            output_summary: str | None = None,
            metadata_json: dict[str, Any] | None = None,
    ) -> ModelCallLog:
        log = ModelCallLog(
            tenant_id=tenant_id,
            request_id=request_id,
            user_id=user_id,
            provider=provider,
            model_name=model_name,
            model_type=model_type,
            call_type=call_type,
            prompt_template_id=prompt_template_id,
            prompt_version_id=prompt_version_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            cost_amount=cost_amount,
            currency=currency,
            latency_ms=latency_ms,
            status=status,
            error_code=error_code,
            error_message=error_message,
            input_summary=input_summary,
            output_summary=output_summary,
            metadata_json=metadata_json,
        )

        self.db_session.add(log)

        try:
            await self.db_session.commit()
            await self.db_session.refresh(log)
        except Exception:
            await self.db_session.rollback()
            raise

        return log
