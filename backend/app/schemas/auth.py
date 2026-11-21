from pydantic import BaseModel, Field, field_validator

from app.schemas.user import UserOut, normalize_phone_number


class PhoneNumberIn(BaseModel):
    phone_number: str = Field(examples=["0555 123 45 67"])

    @field_validator("phone_number")
    @classmethod
    def _normalize(cls, value: str) -> str:
        return normalize_phone_number(value)


class RegisterRequest(PhoneNumberIn):
    pass


class RegisterResponse(BaseModel):
    phone_number: str
    is_new_user: bool
    otp_expires_in_seconds: int
    message: str
    dev_otp_hint: str | None = Field(
        default=None, description="Sadece geliştirme ortamında döner (SMS simülasyonu)."
    )


class VerifyOtpRequest(PhoneNumberIn):
    code: str = Field(pattern=r"^\d{4,6}$", examples=["1234"])


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
