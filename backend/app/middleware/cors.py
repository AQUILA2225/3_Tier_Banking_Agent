
from starlette.middleware.cors import CORSMiddleware
from starlette.types import ASGIApp

from app.core.config import settings


def configure_cors(app: ASGIApp) -> CORSMiddleware:

    return CORSMiddleware(
        app=app,

        allow_origins=settings.cors_allowed_origins,

        allow_credentials=settings.cors_allow_credentials,

        allow_methods=[
            "GET",
            "POST",
            "PUT",
            "PATCH",
            "DELETE",
            "OPTIONS"
        ],

        allow_headers=[
            "Authorization",
            "Content-Type",
            "X-CSRF-Protection",
            "Accept"
        ],

        expose_headers=[
            "X-Request-ID"
        ],

        max_age=settings.cors_max_age
    )
