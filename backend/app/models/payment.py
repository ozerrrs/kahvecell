from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import UUIDPrimaryKeyMixin, utcnow
from app.models.enums import PaymentStatus


class Payment(UUIDPrimaryKeyMixin, Base):
    """Simüle edilmiş mobil ödeme kaydı (başarılı ve başarısız tüm denemeler saklanır)."""

    __tablename__ = "payments"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    plan_id: Mapped[int] = mapped_column(ForeignKey("subscription_plans.id"), nullable=False)
    # Başarılı ödemenin başlattığı abonelik (başarısızsa boş)
    subscription_id: Mapped[str | None] = mapped_column(ForeignKey("subscriptions.id"))
    transaction_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus), nullable=False)
    card_last4: Mapped[str] = mapped_column(String(4), nullable=False)
    failure_reason: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    user: Mapped["User"] = relationship(back_populates="payments")
