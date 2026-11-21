"""Sipariş QR kodu: içerik üretimi, HMAC-SHA256 imzası, doğrulama ve PNG çizimi.

QR içeriği (case dokümanı 13.2):
    {"order_id": "uuid", "user_id": "uuid", "shop_id": "uuid",
     "created_at": "ISO8601", "signature": "hmac-sha256"}

İmza sadece sunucunun bildiği QR_SECRET_KEY ile üretilir. Alanlardan biri bile
değiştirilirse imza tutmaz; anahtarı bilmeyen biri geçerli bir QR üretemez.
"""

import hashlib
import hmac
import io
import json
from datetime import datetime

import qrcode

from app.core.config import settings
from app.models.base import as_utc

SIGNED_FIELDS = ("order_id", "user_id", "shop_id", "created_at")


def format_timestamp(value: datetime) -> str:
    """İmzada kullanılan sabit biçim: 2026-11-21T10:15:30Z"""
    return as_utc(value).isoformat(timespec="seconds").replace("+00:00", "Z")


def sign(order_id: str, user_id: str, shop_id: str, created_at: str) -> str:
    message = "|".join((order_id, user_id, shop_id, created_at)).encode()
    return hmac.new(settings.qr_secret_key.encode(), message, hashlib.sha256).hexdigest()


def build_payload(order_id: str, user_id: str, shop_id: str, created_at: datetime) -> dict:
    created = format_timestamp(created_at)
    return {
        "order_id": order_id,
        "user_id": user_id,
        "shop_id": shop_id,
        "created_at": created,
        "signature": sign(order_id, user_id, shop_id, created),
    }


def encode(payload: dict) -> str:
    """QR'a yazılacak metin (kompakt JSON)."""
    return json.dumps(payload, separators=(",", ":"))


class InvalidQr(Exception):
    """QR okunamadı veya imzası geçersiz."""


def parse_and_verify(data: str) -> dict:
    """QR metnini çözer ve imzasını doğrular. Geçersizse InvalidQr fırlatır."""
    try:
        payload = json.loads(data)
    except (TypeError, ValueError):
        raise InvalidQr("QR kodu okunamadı.")
    if not isinstance(payload, dict) or not all(isinstance(payload.get(f), str) for f in (*SIGNED_FIELDS, "signature")):
        raise InvalidQr("QR kodu KahveCell sipariş biçiminde değil.")
    expected = sign(*(payload[f] for f in SIGNED_FIELDS))
    if not hmac.compare_digest(expected, payload["signature"]):
        raise InvalidQr("QR kodu sahte veya değiştirilmiş (imza geçersiz).")
    return payload


def render_png(data: str) -> bytes:
    image = qrcode.make(data, box_size=8, border=2)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()
