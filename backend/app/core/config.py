from functools import lru_cache
from pathlib import Path 
from typing import Literal 

from pydantic import Field
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