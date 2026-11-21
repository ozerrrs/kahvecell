from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, Numeric, String
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

    subscriptions: Mapped[list["Subscription"]] = relationship(back_populates="plan")


class Subscription(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Bir kullanıcının belirli bir dönemdeki aboneliği."""

    __tablename__ = "subscriptions"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    plan_id: Mapped[int] = mapped_column(ForeignKey("subscription_plans.id"), nullable=False)
    # None = sınırsız paket
    remaining_credits: Mapped[int | None] = mapped_column(Integer)
    remaining_guest_credits: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus), default=SubscriptionStatus.ACTIVE, nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    user: Mapped["User"] = relationship(back_populates="subscriptions")
    plan: Mapped["SubscriptionPlan"] = relationship(back_populates="subscriptions")
    orders: Mapped[list["Order"]] = relationship(back_populates="subscription")

    __table_args__ = (Index("ix_subscriptions_user_status", "user_id", "status"),)
