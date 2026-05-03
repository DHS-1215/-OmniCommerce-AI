from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BaseAppException
from app.services.order_service import OrderService
from app.tools.base import (
    ToolResult,
    business_error_result,
    to_plain_data,
    unexpected_error_result,
)


class OrderTools:
    """智能客服 Agent 可调用的订单工具。"""

    def __init__(
        self,
        db: AsyncSession,
        order_service: OrderService,
    ) -> None:
        self.db = db
        self.order_service = order_service

    async def list_orders(
        self,
        *,
        tenant_id: UUID,
        user_no: str | None = None,
        order_status: str | None = None,
        payment_status: str | None = None,
        fulfillment_status: str | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> ToolResult:
        tool_name = "list_orders"

        try:
            result = await self.order_service.list_orders(
                self.db,
                tenant_id=tenant_id,
                page=page,
                page_size=page_size,
                user_no=user_no,
                order_status=order_status,
                payment_status=payment_status,
                fulfillment_status=fulfillment_status,
            )
            return ToolResult.ok(
                tool_name=tool_name,
                data=to_plain_data(result),
            )
        except BaseAppException as exc:
            return business_error_result(tool_name, exc)
        except Exception as exc:
            return unexpected_error_result(tool_name, exc)

    async def get_order_detail(
        self,
        *,
        tenant_id: UUID,
        order_no: str,
    ) -> ToolResult:
        tool_name = "get_order_detail"

        try:
            result = await self.order_service.get_order_detail(
                self.db,
                tenant_id=tenant_id,
                order_no=order_no,
            )
            return ToolResult.ok(
                tool_name=tool_name,
                data=to_plain_data(result),
            )
        except BaseAppException as exc:
            return business_error_result(tool_name, exc)
        except Exception as exc:
            return unexpected_error_result(tool_name, exc)