import re
from functools import lru_cache
from pathlib import Path 
from typing import Literal 
from urllib.parse import urlsplit

from pydantic import Field, field_validator, SecretStr, model_validator
from sqlalchemy import URL
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
    auth_cookie_secure: bool = True
    
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

    # Database Configuration
    db_host: str = "localhost"
    db_port: int = Field(default=5432, ge=1, le=65535)
    db_name: str = "banking_agent_db"
    db_user: str = "banking_app"
    db_password: SecretStr = Field(min_length=1)
    
    # JWT Security Configuration
    jwt_secret_key: SecretStr = Field(
        min_length=64,
        max_length=64
    )

    jwt_algorithm: Literal["HS256"] = "HS256"
    jwt_issuer: str = Field(
        default="banking-agent-api",
        min_length=1,
        max_length=100
    )

    jwt_audience: str = Field(
        default="banking-agent-client",
        min_length=1,
        max_length=100
    )

    # Token Expiration
    access_token_expire_minutes: int = Field(
        default=15,
        ge=1,
        le=60
    )
    refresh_token_expire_days: int = Field(
        default=7,
        ge=1,
        le=30
    )

    # Password Policy
    password_min_length: int = Field(
        default=12,
        ge=12,
        le=128
    )
    password_max_length: int = Field(
        default=128,
        ge=12,
        le=128
    )
    
    auth_rate_limit_window_seconds: int = Field(
        default=60,
        ge=1,
        le=3600
    )

    auth_register_rate_limit: int = Field(
        default=5,
        ge=1,
        le=1000
    )

    auth_login_rate_limit: int = Field(
        default=10,
        ge=1,
        le=1000
    )

    auth_refresh_rate_limit: int = Field(
        default=30,
        ge=1,
        le=1000
    )

    auth_logout_rate_limit: int = Field(
        default=30,
        ge=1,
        le=1000
    )

    auth_rate_limit_max_keys: int = Field(
        default=10000,
        ge=100,
        le=100000
    )
    
    @property
    def database_url(self) -> URL:
        return URL.create(
            drivername="postgresql+psycopg",
            username=self.db_user,
            password=self.db_password.get_secret_value(),
            host=self.db_host,
            port=self.db_port,
            database=self.db_name
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
    
            # Validate JWT secret key
    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt_secret_key(
        cls,
        value: SecretStr
    ) -> SecretStr:

        secret = value.get_secret_value()

        if re.fullmatch(r"[0-9a-fA-F]{64}", secret) is None:
            raise ValueError(
                "JWT secret must contain exactly 64 hexadecimal characters."
            )

        return value

    # Validate JWT issuer and audience
    @field_validator("jwt_issuer", "jwt_audience")
    @classmethod
    def validate_jwt_identifier(
        cls,
        value: str
    ) -> str:

        if not value or any(char.isspace() for char in value):
            raise ValueError(
                "JWT identifiers must not contain whitespace."
            )

        return value

    # Validate password policy
    @model_validator(mode="after")
    def validate_password_policy(self):

        if self.password_min_length > self.password_max_length:
            raise ValueError(
                "Minimum password length cannot exceed maximum password length."
            )

        return self
    
    @model_validator(mode="after")
    def validate_auth_cookie_security(self):

        if (
            self.app_env == "production"
            and not self.auth_cookie_secure
        ):
            raise ValueError(
            "Production requires secure authentication cookies."
            )

        return self

    # Environment configuration
    model_config = SettingsConfigDict(
        env_file=Base_dir / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        hide_input_in_errors=True
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
settings = get_settings()