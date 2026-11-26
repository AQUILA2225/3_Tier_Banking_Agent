from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.api.v1.router import api_router
from app.api.error_handlers import register_exception_handlers
from app.core.config import settings
from app.core.logging import setup_logging, get_logger
from app.middleware.request_logging import RequestLoggingMiddleware
from app.middleware.cors import configure_cors


# Initialize application logging
setup_logging()
logger = get_logger(__name__)

# Application lifecycle
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Banking Agent API starting")
    logger.info("Environment: %s", settings.app_env)
    logger.info("Application version: %s", settings.app_version)
    logger.debug("Debug logging is enabled")
    logger.info(
        "CORS configured | allowed_origins=%d",
        len(settings.cors_allowed_origins)
    )

    try:
        yield
    finally:
        logger.info("Banking Agent API shutting down")

# Create FastAPI application
fastapi_app = FastAPI(
    title=settings.app_name, 
    description=("AI Banking Agent with Guardrails and Human-in-the-Loop"),
    version=settings.app_version,
    debug=False,
    lifespan=lifespan 
)

# Register middleware
fastapi_app.add_middleware(RequestLoggingMiddleware)

# Register centralized exception handlers
register_exception_handlers(fastapi_app)

@fastapi_app.get("/")
def home():
    logger.debug("Home endpoint accessed")
    return {
        "message": "Welcome to the 3-Tier Banking Agent API",
        "status": "running",
        "environment":settings.app_env
    }

# Register versioned API routes
fastapi_app.include_router(
    api_router,
    prefix=settings.api_v1_prefix
)

# Apply global CORS middleware
app = configure_cors(fastapi_app)
