import re

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from app.models.enums import CupSize, MilkType, UserRole
from app.schemas.common import UtcDatetime

_TR_MOBILE = re.compile(r"^5\d{9}$")
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_phone_number(value: str) -> str:
    """'0555 123 45 67', '5551234567', '+90 555…' → '+905551234567'."""
    digits = re.sub(r"\D", "", value or "")
    if digits.startswith("90") and len(digits) == 12:
        digits = digits[2:]
    elif digits.startswith("0") and len(digits) == 11:
        digits = digits[1:]
    if not _TR_MOBILE.match(digits):
        raise ValueError("Geçerli bir GSM numarası girin (örn. 0555 123 45 67).")
    return f"+90{digits}"


def normalize_full_name(value: str) -> str:
    """Fazla boşlukları temizler, en az 2 karakter ister."""
    value = " ".join((value or "").split())
    if len(value) < 2:
        raise ValueError("Ad soyad en az 2 karakter olmalı.")
    return value


def normalize_email(value: str | None) -> str | None:
    """Boşsa None, doluysa küçük harfe çevirip biçimini kontrol eder."""
    if value is None or value.strip() == "":
        return None
    value = value.strip().lower()
    if not _EMAIL.match(value):
        raise ValueError("Geçerli bir e-posta adresi girin.")
    return value


class UserPreferences(BaseModel):
    favorite_coffees: list[str] = Field(default_factory=list, max_length=20)
    allergens: list[str] = Field(default_factory=list, max_length=20)
    default_size: CupSize | None = None
    default_milk: MilkType | None = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    phone_number: str
    full_name: str | None
    email: str | None
    role: UserRole
    preferences: UserPreferences | None
    created_at: UtcDatetime

    @computed_field
    @property
    def profile_completed(self) -> bool:
        return bool(self.full_name)


class UserUpdate(BaseModel):
    """Profil tamamlama / güncelleme. Gönderilmeyen alanlar değişmez."""

    full_name: str | None = Field(default=None, min_length=2, max_length=100)
    email: str | None = Field(default=None, max_length=255)
    preferences: UserPreferences | None = None

    @field_validator("full_name")
    @classmethod
    def _check_name(cls, value: str | None) -> str | None:
        return None if value is None else normalize_full_name(value)

    @field_validator("email")
    @classmethod
    def _check_email(cls, value: str | None) -> str | None:
        return normalize_email(value)


class RoleUpdate(BaseModel):
    role: UserRole
