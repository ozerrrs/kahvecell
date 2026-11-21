from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import PlanType, SubscriptionStatus
from app.schemas.common import Money, UtcDatetime


class PlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    plan_type: PlanType
    name: str
    monthly_price: Money
    monthly_credits: int | None = Field(description="Aylık kahve hakkı; null = sınırsız")
    guest_credits: int = Field(description="Aylık misafir (arkadaşa ısmarlama) hakkı")
    has_priority: bool
    is_unlimited: bool


class SubscriptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    plan: PlanOut
    status: SubscriptionStatus
    remaining_credits: int | None = Field(description="Kalan kahve hakkı; null = sınırsız")
    remaining_guest_credits: int
    started_at: UtcDatetime
    expires_at: UtcDatetime = Field(description="Dönem sonu: yenileme veya iptal bu tarihte gerçekleşir")
    auto_renew: bool = Field(description="false ise abonelik dönem sonunda sona erer")
    cancelled_at: UtcDatetime | None
    pending_plan: PlanOut | None = Field(description="Bir sonraki dönemde geçilecek paket (düşürme)")


class StartSubscriptionRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {"transaction_id": "TXN-..."}})

    transaction_id: str = Field(description="/payments/process'ten dönen başarılı ödeme numarası")


class ChangePlanRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={
        "example": {"plan_type": "PREMIUM", "transaction_id": "TXN-..."}
    })

    plan_type: PlanType
    transaction_id: str | None = Field(
        default=None, description="Yükseltmede zorunlu (fark ödemesi). Düşürmede gönderilmez."
    )


class SubscriptionActionResult(BaseModel):
    message: str
    subscription: SubscriptionOut
