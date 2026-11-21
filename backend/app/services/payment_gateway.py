"""Mobil ödeme sağlayıcısı simülasyonu (case dokümanı bölüm 12).

Gerçek bir sağlayıcıya geçildiğinde sadece bu sınıfın yerine gerçek entegrasyon yazılır;
servis katmanı değişmez.
"""

from dataclasses import dataclass
from decimal import Decimal

ALWAYS_SUCCESS_CARD = "4242424242424242"
ALWAYS_DECLINED_CARD = "4000000000000002"


@dataclass(frozen=True)
class ChargeResult:
    success: bool
    failure_reason: str | None = None


class MockPaymentGateway:
    def charge(self, card_number: str, amount: Decimal) -> ChargeResult:
        if card_number == ALWAYS_DECLINED_CARD:
            return ChargeResult(success=False, failure_reason="Kart reddedildi (yetersiz bakiye).")
        if amount <= 0:
            return ChargeResult(success=False, failure_reason="Geçersiz tutar.")
        # 4242… ve diğer geçerli (Luhn) kart numaraları başarılı kabul edilir.
        return ChargeResult(success=True)
