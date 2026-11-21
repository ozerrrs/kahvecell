from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.user import (
    UserOut,
    normalize_email,
    normalize_full_name,
    normalize_phone_number,
    validate_password,
)


class PhoneNumberIn(BaseModel):
    phone_number: str = Field(examples=["05551234567"])

    @field_validator("phone_number")
    @classmethod
    def _normalize(cls, value: str) -> str:
        return normalize_phone_number(value)


class RegisterRequest(PhoneNumberIn):
    model_config = ConfigDict(json_schema_extra={"example": {
        "phone_number": "05559998877", "full_name": "Ali Yılmaz", "password": "Kahve123", "email": "ali@example.com",
    }})

    full_name: str = Field(min_length=2, max_length=100)
    password: str = Field(description="En az 8 karakter, en az bir harf ve bir rakam")
    email: str | None = Field(default=None, max_length=255)

    @field_validator("full_name")
    @classmethod
    def _check_name(cls, value: str) -> str:
        return normalize_full_name(value)

    @field_validator("password")
    @classmethod
    def _check_password(cls, value: str) -> str:
        return validate_password(value)

    @field_validator("email")
    @classmethod
    def _check_email(cls, value: str | None) -> str | None:
        return normalize_email(value)


class LoginRequest(PhoneNumberIn):
    model_config = ConfigDict(json_schema_extra={"example": {"phone_number": "05551234567", "password": "Kahve123"}})

    password: str = Field(min_length=1, max_length=128)


class OtpSentResponse(BaseModel):
    phone_number: str
    otp_expires_in_seconds: int
    message: str
    dev_otp_hint: str | None = Field(
        default=None, description="Sadece geliştirme ortamında döner (SMS simülasyonu)."
    )


class VerifyOtpRequest(PhoneNumberIn):
    model_config = ConfigDict(json_schema_extra={"example": {"phone_number": "05551234567", "code": "1234"}})

    code: str = Field(pattern=r"^\d{4,6}$")


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Erişim anahtarının ömrü (saniye)")


class AuthResult(TokenPair):
    is_new_user: bool
    user: UserOut


class RefreshTokenRequest(BaseModel):
    refresh_token: str
