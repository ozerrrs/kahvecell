from sqlalchemy import Boolean, Enum, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import CupSize, MilkType, OrderStatus


class Order(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Bir kullanıcının bir dükkândan, aboneliğini kullanarak verdiği kahve siparişi."""

    __tablename__ = "orders"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    shop_id: Mapped[str] = mapped_column(ForeignKey("shops.id"), nullable=False)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"), nullable=False)
    # Hakkın hangi abonelikten düşüldüğü
    subscription_id: Mapped[str] = mapped_column(ForeignKey("subscriptions.id"), nullable=False)

    # Özelleştirmeler
    size: Mapped[CupSize] = mapped_column(Enum(CupSize), default=CupSize.M, nullable=False)
    milk: Mapped[MilkType] = mapped_column(Enum(MilkType), default=MilkType.NONE, nullable=False)
    sugar: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # kaşık sayısı (0-3)
    extra_shot: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    note: Mapped[str | None] = mapped_column(String(255))
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus), default=OrderStatus.PENDING, nullable=False)
    # QR içeriğindeki HMAC-SHA256 imzası (sahteciliğe karşı)
    qr_signature: Mapped[str | None] = mapped_column(String(128))

    user: Mapped["User"] = relationship(back_populates="orders")
    shop: Mapped["Shop"] = relationship(back_populates="orders")
    product: Mapped["Product"] = relationship(back_populates="orders")
    subscription: Mapped["Subscription"] = relationship(back_populates="orders")

    __table_args__ = (
        Index("ix_orders_user_created", "user_id", "created_at"),
        Index("ix_orders_shop_status", "shop_id", "status"),
    )
