
from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.config import settings

app = FastAPI(
    title=settings.app_name, 
    description=("AI Banking Agent with Guardrails and Human-in-the-Loop"),
    version=settings.app_version,
    debug=settings.debug
)

@app.get("/")
def home():
    return {
        "message": "Welcome to the 3-Tier Banking Agent API",
        "status": "running",
        "environment":settings.app_env
    }


app.include_router(
    api_router,
    prefix=settings.api_v1_prefix
)
