"""Kayıt / giriş iş kuralları: OTP üretme-doğrulama, token verme-yenileme-iptal."""

import logging
from datetime import timedelta

from fastapi import status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AppException
from app.core.passwords import hash_password, verify_password
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_otp,
    verify_otp_hash,
)
from app.models import User
from app.models.base import as_utc, utcnow
from app.models.enums import OtpPurpose
from app.repositories.auth_repository import OtpRepository, RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import AuthResult, OtpSentResponse, TokenPair
from app.schemas.user import UserOut

logger = logging.getLogger("kahvecell.auth")


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)
        self.otps = OtpRepository(db)
        self.refresh_tokens = RefreshTokenRepository(db)

    # ------------------------------------------------------------ kayıt/giriş
    def register(self, phone_number: str, full_name: str, email: str | None, password: str) -> OtpSentResponse:
        """Yeni kullanıcı kaydı: bilgileri (şifre hash'iyle) bekletir ve doğrulama kodu gönderir.

        Hesap, kod doğrulandığında (/verify-otp) oluşturulur.
        """
        if self.users.get_by_phone(phone_number):
            raise AppException(
                status.HTTP_409_CONFLICT, "PHONE_ALREADY_REGISTERED",
                "Bu numara zaten kayıtlı. Giriş yapabilirsiniz.",
            )
        return self._send_otp(
            phone_number, OtpPurpose.REGISTER,
            full_name=full_name, email=email, password_hash=hash_password(password),
        )

    def login(self, phone_number: str, password: str) -> OtpSentResponse:
        """Giriş 1. adım: telefon + şifre doğruysa SMS kodu gönderir (2. adım: /verify-otp).

        Numara kayıtlı değilse de aynı hata döner; böylece hangi numaraların kayıtlı olduğu öğrenilemez.
        """
        user = self.users.get_by_phone(phone_number)
        if not verify_password(password, user.password_hash if user else None):
            logger.info("login_failed phone=%s", _mask(phone_number))
            raise AppException(
                status.HTTP_401_UNAUTHORIZED, "INVALID_CREDENTIALS", "Telefon numarası veya şifre hatalı."
            )
        return self._send_otp(phone_number, OtpPurpose.LOGIN)

    def _send_otp(
        self,
        phone_number: str,
        purpose: OtpPurpose,
        full_name: str | None = None,
        email: str | None = None,
        password_hash: str | None = None,
    ) -> OtpSentResponse:
        code = settings.otp_simulated_code
        expires_in = settings.otp_expire_minutes * 60

        self.otps.invalidate_active(phone_number)
        self.otps.create(
            phone_number, purpose, hash_otp(phone_number, code),
            utcnow() + timedelta(seconds=expires_in),
            pending_full_name=full_name, pending_email=email, pending_password_hash=password_hash,
        )
        self.db.commit()

        logger.info("otp_sent phone=%s purpose=%s (SMS simülasyonu)", _mask(phone_number), purpose.value)
        return OtpSentResponse(
            phone_number=phone_number,
            otp_expires_in_seconds=expires_in,
            message="Doğrulama kodu SMS ile gönderildi. /auth/verify-otp ile doğrulayın.",
            dev_otp_hint=code if settings.is_development else None,
        )

    def verify_otp(self, phone_number: str, code: str) -> AuthResult:
        otp = self.otps.get_latest_unused(phone_number)
        if otp is None or as_utc(otp.expires_at) < utcnow():
            raise AppException(
                status.HTTP_400_BAD_REQUEST, "OTP_EXPIRED",
                "Doğrulama kodu bulunamadı veya süresi doldu. Lütfen yeni kod isteyin.",
            )
        if otp.attempts >= settings.otp_max_attempts:
            raise AppException(
                status.HTTP_429_TOO_MANY_REQUESTS, "OTP_TOO_MANY_ATTEMPTS",
                "Çok fazla hatalı deneme. Lütfen yeni kod isteyin.",
            )
        if not verify_otp_hash(phone_number, code, otp.code_hash):
            otp.attempts += 1
            self.db.commit()
            raise AppException(
                status.HTTP_400_BAD_REQUEST, "OTP_INVALID", "Doğrulama kodu hatalı.",
                {"remaining_attempts": max(settings.otp_max_attempts - otp.attempts, 0)},
            )

        otp.is_used = True
        user = self.users.get_by_phone(phone_number)
        is_new_user = otp.purpose == OtpPurpose.REGISTER

        if is_new_user:
            if user is not None:  # Kod beklerken aynı numara başka yoldan kaydolmuş.
                self.db.commit()
                raise AppException(
                    status.HTTP_409_CONFLICT, "PHONE_ALREADY_REGISTERED", "Bu numara zaten kayıtlı."
                )
            user = self.users.create(
                phone_number, full_name=otp.pending_full_name, email=otp.pending_email,
                password_hash=otp.pending_password_hash,
            )
            logger.info("user_registered user_id=%s", user.id)
        elif user is None:
            self.db.commit()
            raise AppException(status.HTTP_404_NOT_FOUND, "USER_NOT_FOUND", "Kullanıcı bulunamadı.")

        tokens = self._issue_tokens(user)
        self.db.commit()
        logger.info("user_logged_in user_id=%s role=%s", user.id, user.role.value)
        return AuthResult(**tokens.model_dump(), is_new_user=is_new_user, user=UserOut.model_validate(user))

    # --------------------------------------------------------------- tokens
    def refresh(self, refresh_token: str) -> TokenPair:
        """Yenileme anahtarını tek kullanımlık olarak tüketir ve yeni bir çift verir (rotation)."""
        payload = decode_token(refresh_token, "refresh")
        stored = self.refresh_tokens.get(payload.get("jti", ""))
        invalid = AppException(
            status.HTTP_401_UNAUTHORIZED, "INVALID_REFRESH_TOKEN", "Oturum geçersiz, lütfen tekrar giriş yapın."
        )
        if stored is None or stored.user_id != payload["sub"]:
            raise invalid
        if stored.revoked_at is not None:
            # Kullanılmış bir anahtar tekrar geldiyse çalınmış olabilir → tüm oturumları kapat.
            self.refresh_tokens.revoke_all_for_user(stored.user_id)
            self.db.commit()
            logger.warning("refresh_token_reuse_detected user_id=%s", stored.user_id)
            raise invalid
        if as_utc(stored.expires_at) < utcnow():
            raise invalid

        user = self.users.get_by_id(stored.user_id)
        if user is None:
            raise invalid

        self.refresh_tokens.revoke(stored)
        tokens = self._issue_tokens(user)
        self.db.commit()
        return tokens

    def logout(self, refresh_token: str) -> None:
        try:
            payload = decode_token(refresh_token, "refresh")
        except AppException:
            return  # Zaten geçersiz anahtar: çıkış yapılmış sayılır.
        stored = self.refresh_tokens.get(payload.get("jti", ""))
        if stored and stored.revoked_at is None:
            self.refresh_tokens.revoke(stored)
            self.db.commit()

    def _issue_tokens(self, user: User) -> TokenPair:
        access_token, expires_in = create_access_token(user.id, user.role.value)
        refresh_token, jti, refresh_expires_at = create_refresh_token(user.id)
        self.refresh_tokens.create(jti, user.id, refresh_expires_at)
        return TokenPair(access_token=access_token, refresh_token=refresh_token, expires_in=expires_in)


def _mask(phone_number: str) -> str:
    """Loglarda kişisel veriyi gizler: +90555*****67"""
    return phone_number[:6] + "*" * (len(phone_number) - 8) + phone_number[-2:]
