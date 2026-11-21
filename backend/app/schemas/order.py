from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import CupSize, MilkType, OrderStatus, UserRole
from app.schemas.common import UtcDatetime


class OrderCreate(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {
        "shop_id": "<GET /shops'tan bir dükkân id'si>",
        "product_id": "<GET /shops/{id}/menu'den bir ürün id'si>",
        "size": "M", "milk": "OAT", "sugar": 1, "extra_shot": 0, "note": "Az sıcak olsun",
    }})

    shop_id: str
    product_id: str
    size: CupSize = CupSize.M
    milk: MilkType = MilkType.NONE
    sugar: int = Field(default=0, ge=0, le=3, description="Şeker (kaşık)")
    extra_shot: int = Field(default=0, ge=0, le=2, description="Ek espresso shot")
    note: str | None = Field(default=None, max_length=200)

    @field_validator("note")
    @classmethod
    def _clean_note(cls, value: str | None) -> str | None:
        value = " ".join((value or "").split())
        return value or None


class OrderStatusUpdate(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {"status": "ACCEPTED"}})

    status: OrderStatus
    qr_data: str | None = Field(
        default=None, description="DELIVERED için zorunlu: müşterinin QR kodundan okunan metin"
    )


class FavoriteUpdate(BaseModel):
    is_favorite: bool


class QrVerifyRequest(BaseModel):
    qr_data: str = Field(description="QR koddan okunan metin (JSON)")


class QrPayload(BaseModel):
    order_id: str
    user_id: str
    shop_id: str
    created_at: str
    signature: str


class OrderQr(BaseModel):
    payload: QrPayload
    data: str = Field(description="QR koda yazılan metin; dükkân bunu okutur")
    image_url: str = Field(description="QR kodun PNG görseli")


class OrderShopOut(BaseModel):
    id: str
    name: str
    address: str


class OrderProductOut(BaseModel):
    id: str
    name: str
    category: str


class StatusEventOut(BaseModel):
    status: OrderStatus
    changed_at: UtcDatetime
    changed_by_role: UserRole | None


class OrderOut(BaseModel):
    id: str
    status: OrderStatus
    next_statuses: list[OrderStatus] = Field(description="Bu siparişin geçebileceği durumlar")
    shop: OrderShopOut
    product: OrderProductOut
    size: CupSize
    milk: MilkType
    sugar: int
    extra_shot: int
    note: str | None
    customer_name: str | None
    is_priority: bool = Field(description="Unlimited abone — dükkân listesinde öne alınır")
    is_favorite: bool
    credit_used: bool
    created_at: UtcDatetime
    updated_at: UtcDatetime
    history: list[StatusEventOut]
    qr: OrderQr | None = Field(description="Sadece siparişi veren müşteriye gösterilir")


class OrderCreateResult(BaseModel):
    order: OrderOut
    remaining_credits: int | None = Field(description="Kalan kahve hakkı; null = sınırsız")


class QrVerifyResult(BaseModel):
    valid: bool
    reason: str | None = None
    can_deliver: bool = False
    order: OrderOut | None = None
