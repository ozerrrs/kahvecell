import re
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from app.models.enums import PaymentPurpose, PaymentStatus, PlanType
from app.schemas.common import Money, UtcDatetime


def _luhn_valid(number: str) -> bool:
    """Kart numarasının matematiksel olarak geçerli olup olmadığını kontrol eder (Luhn algoritması)."""
    total = 0
    for index, char in enumerate(reversed(number)):
        digit = int(char)
        if index % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0


class CardIn(BaseModel):
    """Kart formu. Kart numarasının tamamı hiçbir yerde saklanmaz; sadece son 4 hanesi kaydedilir."""

    card_number: str = Field(description="Test: 4242-4242-4242-4242 başarılı, 4000-0000-0000-0002 başarısız")
    card_holder: str = Field(min_length=2, max_length=100)
    expiry: str = Field(description="AA/YY biçiminde son kullanma tarihi", examples=["12/28"])
    cvv: str = Field(pattern=r"^\d{3,4}$")

    @field_validator("card_number")
    @classmethod
    def _check_number(cls, value: str) -> str:
        digits = re.sub(r"[\s-]", "", value)
        if not digits.isdigit() or not 13 <= len(digits) <= 19 or not _luhn_valid(digits):
            raise ValueError("Geçersiz kart numarası.")
        return digits

    @field_validator("card_holder")
    @classmethod
    def _check_holder(cls, value: str) -> str:
        return " ".join(value.split()).upper()

    @field_validator("expiry")
    @classmethod
    def _check_expiry(cls, value: str) -> str:
        match = re.fullmatch(r"(0[1-9]|1[0-2])/(\d{2})", value.strip())
        if not match:
            raise ValueError("Son kullanma tarihi AA/YY biçiminde olmalı (örn. 12/28).")
        month, year = int(match.group(1)), 2000 + int(match.group(2))
        now = datetime.now(timezone.utc)
        if (year, month) < (now.year, now.month):
            raise ValueError("Kartın son kullanma tarihi geçmiş.")
        return value.strip()


class PaymentProcessRequest(CardIn):
    model_config = ConfigDict(json_schema_extra={"example": {
        "plan_type": "STARTER",
        "card_number": "4242-4242-4242-4242",
        "card_holder": "Ali Yılmaz",
        "expiry": "12/28",
        "cvv": "123",
    }})

    plan_type: PlanType


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    transaction_id: str
    status: PaymentStatus
    purpose: PaymentPurpose
    plan_type: PlanType
    amount: Money
    card_last4: str
    failure_reason: str | None
    subscription_id: str | None = Field(description="Ödemenin bağlandığı abonelik; null = henüz kullanılmadı")
    timestamp: UtcDatetime

    @computed_field
    @property
    def success(self) -> bool:
        return self.status == PaymentStatus.SUCCESS

    @classmethod
    def from_model(cls, payment) -> "PaymentOut":
        return cls(
            transaction_id=payment.transaction_id,
            status=payment.status,
            purpose=payment.purpose,
            plan_type=payment.plan.plan_type,
            amount=payment.amount,
            card_last4=payment.card_last4,
            failure_reason=payment.failure_reason,
            subscription_id=payment.subscription_id,
            timestamp=payment.created_at,
        )
