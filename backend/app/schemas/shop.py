import enum
from datetime import time

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import Money


class ShopSort(str, enum.Enum):
    DISTANCE = "distance"
    RATING = "rating"
    NAME = "name"


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    category: str
    description: str | None
    base_price: Money
    image_url: str | None
    is_available: bool


class MenuCategory(BaseModel):
    category: str
    items: list[ProductOut]


class ShopSummary(BaseModel):
    """Liste ve harita için dükkân özeti."""

    id: str
    name: str
    address: str
    city: str
    latitude: float
    longitude: float
    rating: float
    photo_url: str | None
    opens_at: time
    closes_at: time
    is_open_now: bool
    distance_km: float | None = Field(description="Gönderilen konuma uzaklık (km); konum yoksa null")


class ShopDetail(ShopSummary):
    description: str | None
    menu: list[MenuCategory]
