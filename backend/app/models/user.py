from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import UUIDPrimaryKeyMixin, utcnow
from app.models.enums import UserRole


class User(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "users"

    phone_number: Mapped[str] = mapped_column(String(15), unique=True, index=True, nullable=False)
    # OTP doğrulandıktan sonra "profil tamamlama" adımında doldurulur, bu yüzden başta boş olabilir.
    full_name: Mapped[str | None] = mapped_column(String(100))
    email: Mapped[str | None] = mapped_column(String(255))
    # scrypt hash'i (bkz. app.core.passwords). Düz şifre hiçbir yerde saklanmaz.
    password_hash: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.CUSTOMER, nullable=False)
    # Örn: {"favorite_coffees": ["latte"], "allergens": ["lactose"]}
    preferences: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    subscriptions: Mapped[list["Subscription"]] = relationship(back_populates="user")
    orders: Mapped[list["Order"]] = relationship(back_populates="user")
    payments: Mapped[list["Payment"]] = relationship(back_populates="user")
    owned_shops: Mapped[list["Shop"]] = relationship(back_populates="owner")
