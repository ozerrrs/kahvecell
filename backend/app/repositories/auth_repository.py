from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models import OtpCode, RefreshToken
from app.models.base import utcnow
from app.models.enums import OtpPurpose


class OtpRepository:
    def __init__(self, db: Session):
        self.db = db

    def invalidate_active(self, phone_number: str) -> None:
        """Yeni kod istendiğinde eski, kullanılmamış kodları geçersiz kılar."""
        self.db.execute(
            update(OtpCode)
            .where(OtpCode.phone_number == phone_number, OtpCode.is_used.is_(False))
            .values(is_used=True)
        )

    def create(
        self,
        phone_number: str,
        purpose: OtpPurpose,
        code_hash: str,
        expires_at: datetime,
        pending_full_name: str | None = None,
        pending_email: str | None = None,
        pending_password_hash: str | None = None,
    ) -> OtpCode:
        otp = OtpCode(
            phone_number=phone_number,
            purpose=purpose,
            code_hash=code_hash,
            expires_at=expires_at,
            pending_full_name=pending_full_name,
            pending_email=pending_email,
            pending_password_hash=pending_password_hash,
        )
        self.db.add(otp)
        self.db.flush()
        return otp

    def get_latest_unused(self, phone_number: str) -> OtpCode | None:
        return self.db.scalar(
            select(OtpCode)
            .where(OtpCode.phone_number == phone_number, OtpCode.is_used.is_(False))
            .order_by(OtpCode.created_at.desc())
            .limit(1)
        )


class RefreshTokenRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, jti: str, user_id: str, expires_at: datetime) -> RefreshToken:
        token = RefreshToken(jti=jti, user_id=user_id, expires_at=expires_at)
        self.db.add(token)
        self.db.flush()
        return token

    def get(self, jti: str) -> RefreshToken | None:
        return self.db.get(RefreshToken, jti)

    def revoke(self, token: RefreshToken) -> None:
        token.revoked_at = utcnow()

    def revoke_all_for_user(self, user_id: str) -> None:
        self.db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=utcnow())
        )
