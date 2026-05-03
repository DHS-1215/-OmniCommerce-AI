# -*- coding: utf-8 -*-
"""
创建时间    :2026/04/26 16:41
IDE       :PyCharm
作者      :董宏升

先把全局异常类型都立住
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from typing import Any, Optional

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette import status

from app.core.response import error_response


class BaseAppException(Exception):
    """
    应用基础异常。

    所有业务异常都应继承该异常，避免直接向前端暴露 Python 原始异常。
    """

    def __init__(
            self,
            code: str = "INTERNAL_SERVER_ERROR",
            message: str = "Internal server error",
            status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
            data: Optional[Any] = None,
    ) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        self.data = data
        super().__init__(message)


class ValidationException(BaseAppException):
    def __init__(self, message: str = "Validation failed", data: Optional[Any] = None):
        super().__init__(
            code="VALIDATION_ERROR",
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            data=data,
        )


class UnauthorizedException(BaseAppException):
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(
            code="UNAUTHORIZED",
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


class ForbiddenException(BaseAppException):
    def __init__(self, message: str = "Forbidden"):
        super().__init__(
            code="FORBIDDEN",
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
        )


class NotFoundException(BaseAppException):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(
            code="NOT_FOUND",
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
        )


class ConflictException(BaseAppException):
    def __init__(self, message: str = "Conflict"):
        super().__init__(
            code="CONFLICT",
            message=message,
            status_code=status.HTTP_409_CONFLICT,
        )


class BusinessException(BaseAppException):
    def __init__(
            self,
            code: str = "BUSINESS_ERROR",
            message: str = "Business error",
            data: Optional[Any] = None,
    ):
        super().__init__(
            code=code,
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            data=data,
        )


class ExternalServiceException(BaseAppException):
    def __init__(
            self,
            message: str = "External service failed",
            code: str = "EXTERNAL_SERVICE_ERROR",
            data: Optional[Any] = None,
    ):
        super().__init__(
            code=code,
            message=message,
            status_code=status.HTTP_502_BAD_GATEWAY,
            data=data,
        )


class ModelGatewayException(BaseAppException):
    def __init__(
            self,
            message: str = "Model gateway failed",
            code: str = "MODEL_GATEWAY_ERROR",
            data: Optional[Any] = None,
    ):
        super().__init__(
            code=code,
            message=message,
            status_code=status.HTTP_502_BAD_GATEWAY,
            data=data,
        )


class AgentExecutionException(BaseAppException):
    def __init__(self, message: str = "Agent execution failed"):
        super().__init__(
            code="AGENT_EXECUTION_ERROR",
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


class RagException(BaseAppException):
    def __init__(self, message: str = "RAG failed"):
        super().__init__(
            code="RAG_ERROR",
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


def get_request_id(request: Request) -> Optional[str]:
    return getattr(request.state, "request_id", None)


async def base_app_exception_handler(
        request: Request,
        exc: BaseAppException,
) -> JSONResponse:
    response = error_response(
        code=exc.code,
        message=exc.message,
        data=exc.data,
        request_id=get_request_id(request),
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=response.model_dump(),
    )


async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
) -> JSONResponse:
    response = error_response(
        code="VALIDATION_ERROR",
        message="Request validation failed",
        data=exc.errors(),
        request_id=get_request_id(request),
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=response.model_dump(),
    )


async def unhandled_exception_handler(
        request: Request,
        exc: Exception,
) -> JSONResponse:
    response = error_response(
        code="INTERNAL_SERVER_ERROR",
        message="Internal server error",
        request_id=get_request_id(request),
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=response.model_dump(),
    )
