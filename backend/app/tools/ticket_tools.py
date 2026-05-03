from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BaseAppException
from app.schemas.ticket import CustomerServiceTicketCreateRequest
from app.services.ticket_service import CustomerServiceTicketService
from app.tools.base import (
    ToolResult,
    business_error_result,
    to_plain_data,
    unexpected_error_result,
)


class TicketTools:
    """智能客服 Agent 可调用的客服工单工具。"""

    def __init__(
        self,
        db: AsyncSession,
        ticket_service: CustomerServiceTicketService,
    ) -> None:
        self.db = db
        self.ticket_service = ticket_service

    async def list_tickets(
        self,
        *,
        tenant_id: UUID,
        user_no: str | None = None,
        order_no: str | None = None,
        status: str | None = None,
        category: str | None = None,
        priority: str | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> ToolResult:
        tool_name = "list_customer_service_tickets"

        try:
            result = await self.ticket_service.list_tickets(
                self.db,
                tenant_id=tenant_id,
                page=page,
                page_size=page_size,
                user_no=user_no,
                order_no=order_no,
                status_filter=status,
                category=category,
                priority=priority,
            )
            return ToolResult.ok(
                tool_name=tool_name,
                data=to_plain_data(result),
            )
        except BaseAppException as exc:
            return business_error_result(tool_name, exc)
        except Exception as exc:
            return unexpected_error_result(tool_name, exc)

    async def get_ticket_detail(
        self,
        *,
        tenant_id: UUID,
        ticket_no: str,
    ) -> ToolResult:
        tool_name = "get_customer_service_ticket_detail"

        try:
            result = await self.ticket_service.get_ticket_detail(
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

    async def create_customer_service_ticket(
        self,
        *,
        payload: CustomerServiceTicketCreateRequest,
    ) -> ToolResult:
        tool_name = "create_customer_service_ticket"

        try:
            result = await self.ticket_service.create_ticket(
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