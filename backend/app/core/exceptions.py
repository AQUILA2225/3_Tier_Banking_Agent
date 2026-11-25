
from typing import Any


class AppException(Exception):
    def __init__(
        self,
        message: str,
        code: str = "APPLICATION_ERROR",
        status_code: int = 400,
        details: Any = None
    ):
        super().__init__(message)

        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details


class BadRequestException(AppException):
    def __init__(
        self,
        message: str = "Invalid request.",
        code: str = "BAD_REQUEST"
    ):
        super().__init__(
            message=message,
            code=code,
            status_code=400
        )


class UnauthorizedException(AppException):
    def __init__(
        self,
        message: str = "Authentication required."
    ):
        super().__init__(
            message=message,
            code="UNAUTHORIZED",
            status_code=401
        )


class ForbiddenException(AppException):
    def __init__(
        self,
        message: str = "Access denied."
    ):
        super().__init__(
            message=message,
            code="FORBIDDEN",
            status_code=403
        )


class NotFoundException(AppException):
    def __init__(
        self,
        message: str = "Requested resource not found.",
        code: str = "NOT_FOUND"
    ):
        super().__init__(
            message=message,
            code=code,
            status_code=404
        )


class ConflictException(AppException):
    def __init__(
        self,
        message: str = "Resource conflict.",
        code: str = "CONFLICT"
    ):
        super().__init__(
            message=message,
            code=code,
            status_code=409
        )


class ServiceUnavailableException(AppException):
    def __init__(
        self,
        message: str = "Service temporarily unavailable."
    ):
        super().__init__(
            message=message,
            code="SERVICE_UNAVAILABLE",
            status_code=503
        )
