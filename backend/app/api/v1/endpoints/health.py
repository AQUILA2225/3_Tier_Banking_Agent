from fastapi import APIRouter
from app.core.logging import get_logger

router = APIRouter(
    prefix="/health",
    tags=["Health"]
)

logger = get_logger(__name__)

@router.get("")
def health_check():
    logger.debug("Health check endpoint accessed")
    return{
        "status": "healthy",
        "service": "banking-agent-backend"
    }
    
    