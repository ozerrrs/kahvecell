"""JWT üretimi/doğrulaması ve OTP hash'leme."""

import hashlib
import hmac
import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal

import jwt
from fastapi import status

from app.core.config import settings
from app.core.exceptions import AppException

TokenType = Literal["access", "refresh"]


def _encode(payload: dict) -> str:
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(user_id: str, role: str) -> tuple[str, int]:
    """Kısa ömürlü erişim anahtarı üretir. (token, saniye cinsinden ömür) döner."""
    now = datetime.now(timezone.utc)
    expires_in = settings.access_token_expire_minutes * 60
    token = _encode({
        "sub": user_id,
        "role": role,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
    })
    return token, expires_in


def create_refresh_token(user_id: str) -> tuple[str, str, datetime]:
    """Uzun ömürlü yenileme anahtarı üretir. (token, jti, bitiş zamanı) döner."""
    now = datetime.now(timezone.utc)
    jti = str(uuid.uuid4())
    expires_at = now + timedelta(days=settings.refresh_token_expire_days)
    token = _encode({"sub": user_id, "type": "refresh", "jti": jti, "iat": now, "exp": expires_at})
    return token, jti, expires_at


def decode_token(token: str, expected_type: TokenType) -> dict:
    """Token'ı doğrular; geçersizse 401 fırlatır."""
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError:
        raise AppException(status.HTTP_401_UNAUTHORIZED, "TOKEN_EXPIRED", "Oturum süresi doldu.")
    except jwt.InvalidTokenError:
        raise AppException(status.HTTP_401_UNAUTHORIZED, "INVALID_TOKEN", "Geçersiz oturum anahtarı.")

    if payload.get("type") != expected_type or "sub" not in payload:
        raise AppException(status.HTTP_401_UNAUTHORIZED, "INVALID_TOKEN", "Geçersiz oturum anahtarı.")
    return payload


def hash_otp(phone_number: str, code: str) -> str:
    """OTP kodunu veritabanında düz metin tutmamak için HMAC ile hash'ler."""
    message = f"{phone_number}:{code}".encode()
    return hmac.new(settings.jwt_secret_key.encode(), message, hashlib.sha256).hexdigest()


def verify_otp_hash(phone_number: str, code: str, expected_hash: str) -> bool:
    return hmac.compare_digest(hash_otp(phone_number, code), expected_hash)
