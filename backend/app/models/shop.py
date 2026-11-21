from datetime import datetime, time
from decimal import Decimal

from sqlalchemy import Boolean, Float, ForeignKey, Index, Numeric, String, Text, Time, event
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.text import fold_text
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
    # Arama için ad + adres + şehrin sadeleştirilmiş hali (bkz. app.core.text.fold_text).
    # Kayıt eklenip güncellendiğinde otomatik doldurulur.
    search_text: Mapped[str | None] = mapped_column(String(500))

    owner: Mapped["User | None"] = relationship(back_populates="owned_shops")
    products: Mapped[list["Product"]] = relationship(
        back_populates="shop", cascade="all, delete-orphan", order_by=lambda: (Product.category, Product.name)
    )
    orders: Mapped[list["Order"]] = relationship(back_populates="shop")

    __table_args__ = (Index("ix_shops_lat_lng", "latitude", "longitude"),)

    def is_open_at(self, moment: datetime) -> bool:
        """Verilen yerel saatte dükkân açık mı? Gece yarısını geçen saatleri de (örn. 08:00–00:00) destekler."""
        now = moment.time()
        if self.opens_at == self.closes_at:
            return True  # 24 saat açık
        if self.opens_at < self.closes_at:
            return self.opens_at <= now < self.closes_at
        return now >= self.opens_at or now < self.closes_at


@event.listens_for(Shop, "before_insert")
@event.listens_for(Shop, "before_update")
def _fill_search_text(_mapper, _connection, shop: Shop) -> None:
    shop.search_text = fold_text(f"{shop.name} {shop.address} {shop.city}")


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
