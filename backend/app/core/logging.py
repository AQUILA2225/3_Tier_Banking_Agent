import logging
from logging.config import dictConfig
from app.core.config import settings

def setup_logging() -> None:
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        
        "formatters": {
            "standard": {
                "format": (
                    "%(asctime)s | "
                    "%(levelname)s | "
                    "%(name)s | "
                    "%(message)s"
                ),
                "datefmt": "%Y-%m-%d %H:%M:%S"
            }
        },
        
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "standard",
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

    