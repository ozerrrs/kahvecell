from datetime import time
from decimal import Decimal

from sqlalchemy import Boolean, Float, ForeignKey, Index, Numeric, String, Text, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class Shop(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Anlaşmalı kahve dükkânı."""

    __tablename__ = "shops"

    owner_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    city: Mapped[str] = mapped_column(String(50), nullable=False)
    # Konum: enlem/boylam ayrı kolonlarda; yakınlık sorgusu Haversine formülüyle yapılacak.
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    opens_at: Mapped[time] = mapped_column(Time, nullable=False)
    closes_at: Mapped[time] = mapped_column(Time, nullable=False)
    rating: Mapped[Decimal] = mapped_column(Numeric(2, 1), default=0, nullable=False)
    photo_url: Mapped[str | None] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    owner: Mapped["User | None"] = relationship(back_populates="owned_shops")
    products: Mapped[list["Product"]] = relationship(back_populates="shop", cascade="all, delete-orphan")
    orders: Mapped[list["Order"]] = relationship(back_populates="shop")

    __table_args__ = (Index("ix_shops_lat_lng", "latitude", "longitude"),)


class Product(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Bir dükkânın menüsündeki ürün."""

    __tablename__ = "products"

    shop_id: Mapped[str] = mapped_column(ForeignKey("shops.id", ondelete="CASCADE"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)  # örn: "Espresso Bazlı", "Filtre", "Soğuk"
    description: Mapped[str | None] = mapped_column(Text)
    base_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(500))
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    shop: Mapped["Shop"] = relationship(back_populates="products")
    orders: Mapped[list["Order"]] = relationship(back_populates="product")
