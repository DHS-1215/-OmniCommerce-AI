# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/05/02 22:25
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.customer_service.service import CustomerServiceAgentService
from app.agents.operation_copilot.service import OperationCopilotAgentService
from app.agents.shopping_guide.service import ShoppingGuideAgentService
from app.core.response import success_response
from app.db.session import get_db_session
from app.schemas.agent import CustomerServiceChatRequest
from app.schemas.operation_copilot import OperationCopilotChatRequest
from app.schemas.shopping_guide import ShoppingGuideChatRequest

router = APIRouter()


@router.post("/customer-service/chat")
async def customer_service_chat(
        payload: CustomerServiceChatRequest,
        request: Request,
        db: AsyncSession = Depends(get_db_session),
):
    """智能客服 Agent 对话接口。"""

    request_id = getattr(request.state, "request_id", None)

    service = CustomerServiceAgentService(db)
    result = await service.chat(
        request=payload,
        request_id=request_id,
    )

    return success_response(data=result)


@router.post("/shopping-guide/chat")
async def shopping_guide_chat(
        payload: ShoppingGuideChatRequest,
        request: Request,
        db: AsyncSession = Depends(get_db_session),
):
    """智能导购 Agent 对话接口。"""

    request_id = getattr(request.state, "request_id", None)

    service = ShoppingGuideAgentService(db)
    result = await service.chat(
        request=payload,
        request_id=request_id,
    )

    return success_response(data=result)


@router.post("/operation-copilot/chat")
async def operation_copilot_chat(
        payload: OperationCopilotChatRequest,
        request: Request,
        db: AsyncSession = Depends(get_db_session),
):
    """运营 Copilot / BI Agent 对话接口。"""

    request_id = getattr(request.state, "request_id", None)

    service = OperationCopilotAgentService(db)
    result = await service.chat(
        request=payload,
        request_id=request_id,
    )

    return success_response(data=result)