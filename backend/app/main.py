
from fastapi import FastAPI

from app.api.v1.router import api_router

app = FastAPI(
    title="3-Tier Banking Agent API",
    description="AI Banking Agent with Guardrails and Human-in-the-Loop",
    version="1.0.0"
)


@app.get("/")
def home():
    return {
        "message": "Welcome to the 3-Tier Banking Agent API",
        "status": "running"
    }


app.include_router(
    api_router,
    prefix="/api/v1"
)
