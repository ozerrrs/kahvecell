from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import UUIDPrimaryKeyMixin, utcnow
from app.models.enums import OtpPurpose


class OtpCode(UUIDPrimaryKeyMixin, Base):
    """Telefona gönderilen (simüle) tek kullanımlık doğrulama kodu.

    Kayıt (REGISTER) kodlarında kullanıcının bilgileri de burada bekletilir;
    hesap ancak telefon doğrulandıktan sonra oluşturulur.
    """

    __tablename__ = "otp_codes"

    phone_number: Mapped[str] = mapped_column(String(15), index=True, nullable=False)
    purpose: Mapped[OtpPurpose] = mapped_column(Enum(OtpPurpose), nullable=False)
    pending_full_name: Mapped[str | None] = mapped_column(String(100))
    pending_email: Mapped[str | None] = mapped_column(String(255))
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class RefreshToken(Base):
    """Verilen yenileme anahtarları — iptal (logout) ve tek kullanım (rotation) için saklanır."""

    __tablename__ = "refresh_tokens"

    jti: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
