from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import PlanType, SubscriptionStatus


class SubscriptionPlan(Base):
    """Paket kataloğu (Starter / Premium / Unlimited). Fiyatlar koda gömülmez, buradan okunur."""

    __tablename__ = "subscription_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plan_type: Mapped[PlanType] = mapped_column(Enum(PlanType), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    monthly_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    # None = sınırsız
    monthly_credits: Mapped[int | None] = mapped_column(Integer)
    guest_credits: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    has_priority: Mapped[bool] = mapped_column(default=False, nullable=False)

    @property
    def is_unlimited(self) -> bool:
        return self.monthly_credits is None


class Subscription(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Bir kullanıcının aboneliği. Her ay aynı kayıt yeni döneme taşınır (yenileme)."""

    __tablename__ = "subscriptions"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    plan_id: Mapped[int] = mapped_column(ForeignKey("subscription_plans.id"), nullable=False)
    # Paket düşürme bir sonraki dönemde uygulanır; o zamana kadar burada bekler.
    pending_plan_id: Mapped[int | None] = mapped_column(ForeignKey("subscription_plans.id"))
    # None = sınırsız paket
    remaining_credits: Mapped[int | None] = mapped_column(Integer)
    remaining_guest_credits: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus), default=SubscriptionStatus.ACTIVE, nullable=False
    )
    auto_renew: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    user: Mapped["User"] = relationship(back_populates="subscriptions")
    plan: Mapped["SubscriptionPlan"] = relationship(foreign_keys=[plan_id], lazy="joined")
    pending_plan: Mapped["SubscriptionPlan | None"] = relationship(foreign_keys=[pending_plan_id], lazy="joined")
    orders: Mapped[list["Order"]] = relationship(back_populates="subscription")

    __table_args__ = (Index("ix_subscriptions_user_status", "user_id", "status"),)
