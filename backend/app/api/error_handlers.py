
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.core.exceptions import AppException
from app.core.logging import get_logger
from app.core.request_context import get_request_id


logger = get_logger(__name__)


# Build a standardized error response
def build_error_response(
    request: Request,
    status_code: int,
    code: str,
    message: str,
    details: Any = None,
    headers: dict[str, str] | None = None
) -> JSONResponse:

    request_id = getattr(
        request.state,
        "request_id",
        get_request_id()
    )

    response_headers = dict(headers or {})

    response_headers["X-Request-ID"] = request_id

    return JSONResponse(
        status_code=status_code,
        headers=response_headers,
        content={
            "success": False,
            "error": {
                "code": code,
                "message": message,
                "details": details,
                "request_id": request_id
            }
        }
    )


# Handle custom application exceptions
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


# Handle HTTP exceptions
async def http_exception_handler(
    request: Request,
    exc: HTTPException
) -> JSONResponse:

    messages = {
        400: "Invalid request.",
        401: "Authentication required.",
        403: "Access denied.",
        404: "Requested resource not found.",
        405: "Method not allowed.",
        409: "Resource conflict.",
        429: "Too many requests.",
        503: "Service temporarily unavailable."
    }

    return build_error_response(
        request=request,
        status_code=exc.status_code,
        code=f"HTTP_{exc.status_code}",
        message=messages.get(
            exc.status_code,
            "Request could not be completed."
        ),
        headers=exc.headers
    )


# Handle request validation errors
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError
) -> JSONResponse:

    errors = []

    for error in exc.errors():

        errors.append({
            "field": ".".join(
                str(item)
                for item in error["loc"]
            ),
            "type": error["type"],
            "message": "Invalid or missing field."
        })

    logger.warning(
        "Request validation failed"
    )

    return build_error_response(
        request=request,
        status_code=422,
        code="VALIDATION_ERROR",
        message="Request validation failed.",
        details=errors
    )


# Handle unexpected internal server errors
async def unhandled_exception_handler(
    request: Request,
    exc: Exception
) -> JSONResponse:

    request_id = getattr(
        request.state,
        "request_id",
        "-"
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


# Register all exception handlers
def register_exception_handlers(
    app: FastAPI
) -> None:

    app.add_exception_handler(
        AppException,
        app_exception_handler
    )

    app.add_exception_handler(
        HTTPException,
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
