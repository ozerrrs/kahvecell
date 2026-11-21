"""Ödeme iş kuralları: tutarı belirler, sahte ödeme sağlayıcısından tahsil eder, sonucu kaydeder."""

import logging

from fastapi import status
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models import User
from app.models.enums import PaymentPurpose, PaymentStatus, PlanType
from app.repositories.payment_repository import PaymentRepository
from app.schemas.payment import CardIn, PaymentOut
from app.services.payment_gateway import MockPaymentGateway
from app.services.subscription_service import SubscriptionService

logger = logging.getLogger("kahvecell.payments")


class PaymentService:
    def __init__(self, db: Session, gateway: MockPaymentGateway | None = None):
        self.db = db
        self.payments = PaymentRepository(db)
        self.subscriptions = SubscriptionService(db)
        self.gateway = gateway or MockPaymentGateway()

    def process(self, user: User, plan_type: PlanType, card: CardIn) -> PaymentOut:
        """Paket için ödeme alır.

        - Aktif abonelik yoksa: paketin tam fiyatı (NEW_SUBSCRIPTION)
        - Daha pahalı pakete geçişte: fiyat farkı (UPGRADE)
        - Aynı / daha ucuz paket: ödeme gerekmez → hata
        """
        plan = self.subscriptions.get_plan(plan_type)
        active = self.subscriptions.get_active(user)

        if active is None:
            purpose, amount = PaymentPurpose.NEW_SUBSCRIPTION, plan.monthly_price
        elif plan.monthly_price > active.plan.monthly_price:
            purpose, amount = PaymentPurpose.UPGRADE, plan.monthly_price - active.plan.monthly_price
        else:
            raise AppException(
                status.HTTP_400_BAD_REQUEST, "PAYMENT_NOT_REQUIRED",
                "Bu paket için ödeme gerekmiyor. Düşürme işlemi ücretsizdir: PATCH /subscriptions/me.",
            )

        result = self.gateway.charge(card.card_number, amount)
        payment = self.payments.create(
            user_id=user.id,
            plan_id=plan.id,
            purpose=purpose,
            amount=amount,
            status=PaymentStatus.SUCCESS if result.success else PaymentStatus.FAILED,
            card_last4=card.card_number[-4:],
            failure_reason=result.failure_reason,
        )
        self.db.commit()
        out = PaymentOut.from_model(payment)
        logger.info("payment_processed user_id=%s txn=%s status=%s amount=%s",
                    user.id, payment.transaction_id, payment.status.value, payment.amount)

        if not result.success:
            raise AppException(
                status.HTTP_402_PAYMENT_REQUIRED, "PAYMENT_DECLINED",
                result.failure_reason or "Ödeme reddedildi.", out.model_dump(mode="json"),
            )
        return out

    def history(self, user: User, offset: int, limit: int) -> list[PaymentOut]:
        return [PaymentOut.from_model(p) for p in self.payments.list_for_user(user.id, offset, limit)]
