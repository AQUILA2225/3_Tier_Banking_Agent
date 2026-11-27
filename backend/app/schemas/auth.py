from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    SecretStr,
    field_validator
)

from app.core.security import validate_password
from app.models import UserRole


def normalize_email(email: str) -> str:

    return email.strip().lower()


class AuthRequest(BaseModel):

    model_config = ConfigDict(
        extra="forbid",
        hide_input_in_errors=True
    )

    email: EmailStr = Field(max_length=255)

    @field_validator("email", mode="before")
    @classmethod
    def validate_email(cls, value):

        if isinstance(value, str):
            return normalize_email(value)

        return value


class RegisterRequest(AuthRequest):

    full_name: str = Field(
        min_length=2,
        max_length=100
    )

    password: SecretStr = Field(
        min_length=12,
        max_length=128
    )

    @field_validator("full_name", mode="before")
    @classmethod
    def normalize_full_name(cls, value):

        if isinstance(value, str):
            return " ".join(value.split())

        return value

    @field_validator("password")
    @classmethod
    def enforce_password_policy(
        cls,
        value: SecretStr
    ) -> SecretStr:

        validate_password(
            value.get_secret_value()
        )

        return value


class LoginRequest(AuthRequest):

    password: SecretStr = Field(
        min_length=1,
        max_length=128
    )


class UserResponse(BaseModel):

    model_config = ConfigDict(
        from_attributes=True
    )

    id: UUID
    full_name: str
    email: EmailStr
    role: UserRole
    is_active: bool
    created_at: datetime


class TokenResponse(BaseModel):

    access_token: str = Field(
        min_length=1,
        max_length=4096,
        repr=False
    )

    token_type: Literal["bearer"] = "bearer"

    expires_in: int = Field(gt=0)


class MessageResponse(BaseModel):

    message: str