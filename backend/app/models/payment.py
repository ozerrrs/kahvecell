from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import UUIDPrimaryKeyMixin, utcnow
from app.models.enums import PaymentPurpose, PaymentStatus


class Payment(UUIDPrimaryKeyMixin, Base):
    """Simüle edilmiş mobil ödeme kaydı (başarılı ve başarısız tüm denemeler saklanır)."""

    __tablename__ = "payments"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    plan_id: Mapped[int] = mapped_column(ForeignKey("subscription_plans.id"), nullable=False)
    purpose: Mapped[PaymentPurpose] = mapped_column(Enum(PaymentPurpose), nullable=False)
    # Ödemenin kullanıldığı abonelik. Boşsa ödeme henüz bir aboneliğe bağlanmamıştır.
    subscription_id: Mapped[str | None] = mapped_column(ForeignKey("subscriptions.id"))
    transaction_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus), nullable=False)
    card_last4: Mapped[str] = mapped_column(String(4), nullable=False)
    failure_reason: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    user: Mapped["User"] = relationship(back_populates="payments")
    plan: Mapped["SubscriptionPlan"] = relationship(lazy="joined")

    __table_args__ = (Index("ix_payments_user_created", "user_id", "created_at"),)
