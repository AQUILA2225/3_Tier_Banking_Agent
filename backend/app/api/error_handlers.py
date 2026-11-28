import logging

from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.core.exceptions import AppException
from app.core.auth_cookies import disable_auth_caching


logger = logging.getLogger(__name__)


# --------------------------------------------------
# Authentication response cache protection
# --------------------------------------------------

def protect_auth_error_response(
    request: Request,
    response: JSONResponse
) -> JSONResponse:

    auth_path = f"{settings.api_v1_prefix}/auth"

    path = request.url.path

    if path == auth_path or path.startswith(
        f"{auth_path}/"
    ):

        disable_auth_caching(response)

    return response


# --------------------------------------------------
# Common error response builder
# --------------------------------------------------

def build_error_response(
    request: Request,
    status_code: int,
    code: str,
    message: str,
    details: list[Any] | None = None,
    headers: dict[str, str] | None = None
) -> JSONResponse:

    request_id = getattr(
        request.state,
        "request_id",
        None
    )

    response_headers = dict(headers or {})

    if request_id is not None:

        request_id = str(request_id)

        response_headers["X-Request-ID"] = request_id

    response = JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error": {
                "code": code,
                "message": message,
                "details": details if details is not None else [],
                "request_id": request_id
            }
        },
        headers=response_headers
    )

    return protect_auth_error_response(
        request,
        response
    )


# --------------------------------------------------
# Custom application exception handler
# --------------------------------------------------

async def app_exception_handler(
    request: Request,
    exc: AppException
) -> JSONResponse:

    logger.warning(
        "Application exception: %s",
        exc.code
    )

    headers = None

    if exc.status_code == 401:

        headers = {
            "WWW-Authenticate": "Bearer"
        }

    return build_error_response(
        request=request,
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        details=exc.details,
        headers=headers
    )


# --------------------------------------------------
# HTTP exception handler
# --------------------------------------------------

async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException
) -> JSONResponse:

    logger.warning(
        "HTTP exception: %s",
        exc.status_code
    )

    try:

        code = HTTPStatus(exc.status_code).name

    except ValueError:

        code = "HTTP_ERROR"

    message = (
        exc.detail
        if isinstance(exc.detail, str)
        else "An HTTP error occurred."
    )

    headers = dict(exc.headers or {})

    if exc.status_code == 401:

        if not any(
            key.lower() == "www-authenticate"
            for key in headers
        ):

            headers["WWW-Authenticate"] = "Bearer"

    return build_error_response(
        request=request,
        status_code=exc.status_code,
        code=code,
        message=message,
        headers=headers
    )


# --------------------------------------------------
# Request validation exception handler
# --------------------------------------------------

async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError
) -> JSONResponse:

    logger.warning(
        "Request validation failed"
    )

    auth_path = f"{settings.api_v1_prefix}/auth"

    path = request.url.path

    if path == auth_path or path.startswith(
        f"{auth_path}/"
    ):

        return build_error_response(
            request=request,
            status_code=422,
            code="VALIDATION_ERROR",
            message="Invalid authentication request.",
            details=[]
        )

    details = []

    for error in exc.errors():

        details.append({
            "field": ".".join(
                str(item)
                for item in error["loc"]
            ),
            "message": error["msg"],
            "type": error["type"]
        })

    return build_error_response(
        request=request,
        status_code=422,
        code="VALIDATION_ERROR",
        message="Request validation failed.",
        details=details
    )


# --------------------------------------------------
# Unexpected server exception handler
# --------------------------------------------------

async def unhandled_exception_handler(
    request: Request,
    exc: Exception
) -> JSONResponse:

    request_id = getattr(
        request.state,
        "request_id",
        None
    )

    logger.error(
        "Unhandled application exception: %s | "
        "failed_request_id=%s",
        type(exc).__name__,
        request_id
    )

    return build_error_response(
        request=request,
        status_code=500,
        code="INTERNAL_SERVER_ERROR",
        message="An unexpected error occurred."
    )


# --------------------------------------------------
# Register all exception handlers
# --------------------------------------------------

def register_exception_handlers(
    app: FastAPI
) -> None:

    app.add_exception_handler(
        AppException,
        app_exception_handler
    )

    app.add_exception_handler(
        StarletteHTTPException,
        http_exception_handler
    )

    app.add_exception_handler(
        RequestValidationError,
        validation_exception_handler
    )

    app.add_exception_handler(
        Exception,
        unhandled_exception_handler
    )