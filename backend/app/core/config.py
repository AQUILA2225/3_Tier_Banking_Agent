from functools import lru_cache
from pathlib import Path 
from typing import Literal 
from urllib.parse import urlsplit

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root directory
Base_dir = Path(__file__).resolve().parents[3]

class Settings(BaseSettings):
    # Application configuration
    app_name: str = "3-Tier Banking Agent API"
    app_version: str = "1.0.0"
    
    app_env: Literal[
        "development",
        "testing",
        "production",
    ] = "development"
    
    debug: bool = False
    
    # API configuration
    api_v1_prefix: str = Field(
        default="/api/v1",
        pattern=r"^/[a-zA-Z0-9/_-]+$"
    )
    
    # Logging Configuration
    log_level: Literal[
        "DEBUG",
        "INFO",
        "WARNING",
        "ERROR",
        "CRITICAL",
    ] = "INFO"
    
    # CORS configuration
    cors_allowed_origins: list[str] = Field(
        default_factory=list
    )

    cors_allow_credentials: bool = False

    cors_max_age: int = Field(
        default=600,
        ge=0,
        le=86400
    )

    # Validate allowed origins
    @field_validator("cors_allowed_origins")
    @classmethod
    def validate_cors_origins(
        cls,
        origins: list[str]
    ) -> list[str]:

        validated_origins = []

        for origin in origins:

            origin = origin.strip()

            if "*" in origin:
                raise ValueError(
                    "Wildcard CORS origins are not allowed."
                )

            parsed = urlsplit(origin)

            if (
                parsed.scheme not in ("http", "https")
                or not parsed.hostname
                or parsed.username is not None
                or parsed.password is not None
                or parsed.path
                or parsed.query
                or parsed.fragment
                or "?" in origin
                or "#" in origin
                or any(char.isspace() for char in origin)
            ):
                raise ValueError(
                    "CORS origins must contain only "
                    "a valid scheme, hostname and optional port."
                )

            # Validate port number if provided
            _ = parsed.port

            validated_origins.append(origin)

        return list(dict.fromkeys(validated_origins))


    # Environment configuration
    model_config = SettingsConfigDict(
        env_file=Base_dir / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False
    )

@lru_cache
def get_settings() -> Settings:
    return Settings()
settings = get_settings()