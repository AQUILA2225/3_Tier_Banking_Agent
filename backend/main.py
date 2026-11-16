from fastapi import FastAPI

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


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "banking-agent-backend"
    }