from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BaseAppException
from app.services.product_service import ProductService
from app.tools.base import (
    ToolResult,
    business_error_result,
    to_plain_data,
    unexpected_error_result,
)


class ProductTools:
    """智能客服 Agent 可调用的商品工具。"""

    def __init__(
        self,
        db: AsyncSession,
        product_service: ProductService,
    ) -> None:
        self.db = db
        self.product_service = product_service

    async def list_products(
        self,
        *,
        tenant_id: UUID,
        keyword: str | None = None,
        brand: str | None = None,
        category: str | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> ToolResult:
        tool_name = "list_products"

        try:
            result = await self.product_service.list_products(
                self.db,
                tenant_id=tenant_id,
                page=page,
                page_size=page_size,
                keyword=keyword,
                brand=brand,
                category=category,
            )
            return ToolResult.ok(
                tool_name=tool_name,
                data=to_plain_data(result),
            )
        except BaseAppException as exc:
            return business_error_result(tool_name, exc)
        except Exception as exc:
            return unexpected_error_result(tool_name, exc)

    async def get_product_detail(
        self,
        *,
        tenant_id: UUID,
        product_no: str,
    ) -> ToolResult:
        tool_name = "get_product_detail"

        try:
            result = await self.product_service.get_product_detail(
                self.db,
                tenant_id=tenant_id,
                product_no=product_no,
            )
            return ToolResult.ok(
                tool_name=tool_name,
                data=to_plain_data(result),
            )
        except BaseAppException as exc:
            return business_error_result(tool_name, exc)
        except Exception as exc:
            return unexpected_error_result(tool_name, exc)

    async def list_product_skus(
        self,
        *,
        tenant_id: UUID,
        product_no: str,
    ) -> ToolResult:
        tool_name = "list_product_skus"

        try:
            result = await self.product_service.list_product_skus(
                self.db,
                tenant_id=tenant_id,
                product_no=product_no,
            )
            return ToolResult.ok(
                tool_name=tool_name,
                data=to_plain_data(result),
            )
        except BaseAppException as exc:
            return business_error_result(tool_name, exc)
        except Exception as exc:
            return unexpected_error_result(tool_name, exc)

    async def get_sku_detail(
        self,
        *,
        tenant_id: UUID,
        sku_no: str,
    ) -> ToolResult:
        tool_name = "get_sku_detail"

        try:
            result = await self.product_service.get_sku_detail(
                self.db,
                tenant_id=tenant_id,
                sku_no=sku_no,
            )
            return ToolResult.ok(
                tool_name=tool_name,
                data=to_plain_data(result),
            )
        except BaseAppException as exc:
            return business_error_result(tool_name, exc)
        except Exception as exc:
            return unexpected_error_result(tool_name, exc)

    async def list_product_reviews(
        self,
        *,
        tenant_id: UUID,
        product_no: str,
        page: int = 1,
        page_size: int = 10,
    ) -> ToolResult:
        tool_name = "list_product_reviews"

        try:
            result = await self.product_service.list_product_reviews(
                self.db,
                tenant_id=tenant_id,
                product_no=product_no,
                page=page,
                page_size=page_size,
            )
            return ToolResult.ok(
                tool_name=tool_name,
                data=to_plain_data(result),
            )
        except BaseAppException as exc:
            return business_error_result(tool_name, exc)
        except Exception as exc:
            return unexpected_error_result(tool_name, exc)