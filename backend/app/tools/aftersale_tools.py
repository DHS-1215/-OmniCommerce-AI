from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BaseAppException
from app.schemas.aftersale import AfterSaleCreateRequest
from app.services.aftersale_service import AfterSaleService
from app.tools.base import (
    ToolResult,
    business_error_result,
    to_plain_data,
    unexpected_error_result,
)


class AftersaleTools:
    """智能客服 Agent 可调用的售后工具。

    注意：
    AfterSaleService 的真实签名要求显式传入 db，
    所以工具初始化时需要接收 AsyncSession。
    """

    def __init__(
        self,
        db: AsyncSession,
        aftersale_service: AfterSaleService,
    ) -> None:
        self.db = db
        self.aftersale_service = aftersale_service

    async def list_aftersales(
        self,
        *,
        tenant_id: UUID,
        user_no: str | None = None,
        order_no: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> ToolResult:
        tool_name = "list_aftersales"

        try:
            result = await self.aftersale_service.list_after_sale_tickets(
                self.db,
                tenant_id=tenant_id,
                page=page,
                page_size=page_size,
                user_no=user_no,
                order_no=order_no,
                status_filter=status,
            )
            return ToolResult.ok(
                tool_name=tool_name,
                data=to_plain_data(result),
            )
        except BaseAppException as exc:
            return business_error_result(tool_name, exc)
        except Exception as exc:
            return unexpected_error_result(tool_name, exc)

    async def get_aftersale_detail(
        self,
        *,
        tenant_id: UUID,
        ticket_no: str,
    ) -> ToolResult:
        tool_name = "get_aftersale_detail"

        try:
            result = await self.aftersale_service.get_after_sale_detail(
                self.db,
                tenant_id=tenant_id,
                ticket_no=ticket_no,
            )
            return ToolResult.ok(
                tool_name=tool_name,
                data=to_plain_data(result),
            )
        except BaseAppException as exc:
            return business_error_result(tool_name, exc)
        except Exception as exc:
            return unexpected_error_result(tool_name, exc)

    async def create_aftersale_ticket(
        self,
        *,
        payload: AfterSaleCreateRequest,
    ) -> ToolResult:
        tool_name = "create_aftersale_ticket"

        try:
            result = await self.aftersale_service.create_after_sale_ticket(
                self.db,
                request=payload,
            )
            return ToolResult.ok(
                tool_name=tool_name,
                data=to_plain_data(result),
            )
        except BaseAppException as exc:
            return business_error_result(tool_name, exc)
        except Exception as exc:
            return unexpected_error_result(tool_name, exc)