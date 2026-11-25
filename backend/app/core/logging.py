import logging
from logging.config import dictConfig
from app.core.config import settings
from app.core.request_context import get_request_id

class RequestIDFilter(logging.Filter):

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        return True

def setup_logging() -> None:
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        
        "filters": {
            "request_id": {
                "()": RequestIDFilter
            }
        },
        
        "formatters": {
            "standard": {
                "format": (
                    "%(asctime)s | "
                    "%(levelname)s | "
                    "%(name)s | "
                    "request_id=%(request_id)s | "
                    "%(message)s"
                ),
                "datefmt": "%Y-%m-%d %H:%M:%S"
            }
        },
        
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "standard",
                "filters": ["request_id"],
                "level": settings.log_level,
                "stream": "ext://sys.stdout"
            }
        },
        
        "loggers": {
            "app": {
                "handlers": ["console"],
                "level": settings.log_level,
                "propagate": False
            }
        }
    }
    
    dictConfig(logging_config)

def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)

    