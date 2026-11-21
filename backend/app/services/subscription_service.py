"""Abonelik iş kuralları: başlatma, yükseltme, düşürme, iptal ve aylık yenileme.

Kurallar
- Başlatma: başarılı bir NEW_SUBSCRIPTION ödemesiyle yapılır; aynı anda tek aktif abonelik olabilir.
- Yükseltme: iki paketin fiyat farkı ödenir; yeni haklar hemen eklenir, dönem bitişi değişmez.
- Düşürme: ücretsizdir; mevcut dönem bitince yeni pakete geçilir (ödenen haklar kaybolmaz).
- İptal: abonelik dönem sonuna kadar kullanılabilir, sonra yenilenmez.
- Yenileme: dönem bitince haklar sıfırlanır ve yeni paket miktarı yüklenir (simüle otomatik ödeme).
"""

import logging
from datetime import timedelta

from fastapi import status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AppException
from app.models import Payment, Subscription, SubscriptionPlan, User
from app.models.base import as_utc, utcnow
from app.models.enums import PaymentPurpose, PaymentStatus, PlanType, SubscriptionStatus
from app.repositories.payment_repository import PaymentRepository
from app.repositories.subscription_repository import SubscriptionPlanRepository, SubscriptionRepository

logger = logging.getLogger("kahvecell.subscriptions")

# Uzun süre hiç istek gelmezse birden çok dönem birikmiş olabilir; sonsuz döngüye karşı üst sınır.
_MAX_ROLLOVERS = 24


class SubscriptionService:
    def __init__(self, db: Session):
        self.db = db
        self.plans = SubscriptionPlanRepository(db)
        self.subscriptions = SubscriptionRepository(db)
        self.payments = PaymentRepository(db)

    # -------------------------------------------------------------- sorgular
    def list_plans(self) -> list[SubscriptionPlan]:
        return self.plans.list()

    def get_plan(self, plan_type: PlanType) -> SubscriptionPlan:
        plan = self.plans.get_by_type(plan_type)
        if plan is None:
            raise AppException(status.HTTP_404_NOT_FOUND, "PLAN_NOT_FOUND", "Paket bulunamadı.")
        return plan

    def get_active(self, user: User) -> Subscription | None:
        """Aktif aboneliği döner; dönemi bitmişse önce yenileme/sonlandırma uygular."""
        subscription = self.subscriptions.get_active_for_user(user.id)
        if subscription is None:
            return None
        if self._roll_over(subscription):
            self.db.commit()
        return subscription if subscription.status == SubscriptionStatus.ACTIVE else None

    def get_active_or_404(self, user: User) -> Subscription:
        subscription = self.get_active(user)
        if subscription is None:
            raise AppException(
                status.HTTP_404_NOT_FOUND, "NO_ACTIVE_SUBSCRIPTION", "Aktif bir aboneliğiniz bulunmuyor."
            )
        return subscription

    # ------------------------------------------------------------- işlemler
    def start(self, user: User, transaction_id: str) -> Subscription:
        if self.get_active(user) is not None:
            raise AppException(
                status.HTTP_409_CONFLICT, "ALREADY_SUBSCRIBED",
                "Zaten aktif bir aboneliğiniz var. Paket değiştirmek için PATCH /subscriptions/me kullanın.",
            )
        payment = self._take_payment(user, transaction_id, PaymentPurpose.NEW_SUBSCRIPTION)

        now = utcnow()
        subscription = self.subscriptions.create(
            user.id, payment.plan, started_at=now, expires_at=now + self._period()
        )
        payment.subscription_id = subscription.id
        self.db.commit()
        logger.info("subscription_started user_id=%s plan=%s txn=%s",
                    user.id, payment.plan.plan_type.value, payment.transaction_id)
        return subscription

    def change_plan(self, user: User, plan_type: PlanType, transaction_id: str | None) -> tuple[Subscription, str]:
        subscription = self.get_active_or_404(user)
        current, target = subscription.plan, self.get_plan(plan_type)

        if target.id == current.id:
            if subscription.pending_plan_id is None and subscription.auto_renew:
                raise AppException(status.HTTP_400_BAD_REQUEST, "SAME_PLAN", "Zaten bu pakettesiniz.")
            # Bekleyen düşürmeyi / iptali geri al.
            subscription.pending_plan_id = None
            self._resume(subscription)
            self.db.commit()
            self.db.refresh(subscription)
            return subscription, "Bekleyen paket değişikliği / iptal geri alındı."

        if target.monthly_price > current.monthly_price:
            return self._upgrade(user, subscription, current, target, transaction_id)
        return self._schedule_downgrade(subscription, target)

    def cancel(self, user: User) -> Subscription:
        subscription = self.get_active_or_404(user)
        if not subscription.auto_renew:
            raise AppException(status.HTTP_409_CONFLICT, "ALREADY_CANCELLED", "Abonelik zaten iptal edilmiş.")
        subscription.auto_renew = False
        subscription.cancelled_at = utcnow()
        subscription.pending_plan_id = None
        self.db.commit()
        self.db.refresh(subscription)
        logger.info("subscription_cancelled user_id=%s ends_at=%s", user.id, subscription.expires_at)
        return subscription

    def simulate_period_end(self, user: User) -> Subscription:
        """Demo: dönem sonunu bugüne çeker ve yenileme mekaniğini çalıştırır."""
        subscription = self.get_active_or_404(user)
        subscription.expires_at = utcnow()
        self._roll_over(subscription)
        self.db.commit()
        return subscription

    # -------------------------------------------------------------- yardımcı
    def _upgrade(self, user, subscription, current, target, transaction_id) -> tuple[Subscription, str]:
        if not transaction_id:
            raise AppException(
                status.HTTP_402_PAYMENT_REQUIRED, "PAYMENT_REQUIRED",
                "Yükseltme için fark ödemesi gerekiyor. Önce /payments/process ile ödeme yapın.",
                {"amount": float(target.monthly_price - current.monthly_price)},
            )
        payment = self._take_payment(user, transaction_id, PaymentPurpose.UPGRADE, expected_plan=target)
        expected_amount = target.monthly_price - current.monthly_price
        if payment.amount != expected_amount:
            raise AppException(
                status.HTTP_400_BAD_REQUEST, "PAYMENT_MISMATCH",
                "Ödeme tutarı mevcut paketinizle uyuşmuyor. Lütfen yeni bir ödeme yapın.",
                {"expected_amount": float(expected_amount), "paid_amount": float(payment.amount)},
            )

        # Haklar: kalan haklara paket farkı eklenir (sınırsıza geçişte sınırsız olur).
        if target.monthly_credits is None:
            subscription.remaining_credits = None
        else:
            subscription.remaining_credits = (subscription.remaining_credits or 0) + (
                target.monthly_credits - (current.monthly_credits or 0)
            )
        subscription.remaining_guest_credits += max(target.guest_credits - current.guest_credits, 0)
        subscription.plan_id = target.id
        subscription.pending_plan_id = None
        self._resume(subscription)
        payment.subscription_id = subscription.id
        self.db.commit()
        self.db.refresh(subscription)
        logger.info("subscription_upgraded user_id=%s %s->%s txn=%s",
                    user.id, current.plan_type.value, target.plan_type.value, payment.transaction_id)
        return subscription, f"{target.name} paketine yükseltildi; yeni haklarınız hemen kullanılabilir."

    def _schedule_downgrade(self, subscription, target) -> tuple[Subscription, str]:
        subscription.pending_plan_id = target.id
        self._resume(subscription)
        self.db.commit()
        self.db.refresh(subscription)
        return subscription, (
            f"Dönem sonunda {target.name} paketine geçilecek. O zamana kadar mevcut haklarınızı kullanabilirsiniz."
        )

    def _take_payment(
        self,
        user: User,
        transaction_id: str,
        purpose: PaymentPurpose,
        expected_plan: SubscriptionPlan | None = None,
    ) -> Payment:
        """Ödemeyi doğrular: bu kullanıcıya ait, başarılı, doğru amaçlı ve daha önce kullanılmamış olmalı."""
        payment = self.payments.get_by_transaction_id(transaction_id)
        if payment is None or payment.user_id != user.id:
            raise AppException(status.HTTP_404_NOT_FOUND, "PAYMENT_NOT_FOUND", "Ödeme bulunamadı.")
        if payment.status != PaymentStatus.SUCCESS:
            raise AppException(status.HTTP_400_BAD_REQUEST, "PAYMENT_NOT_SUCCESSFUL", "Bu ödeme başarısız olmuş.")
        if payment.subscription_id is not None:
            raise AppException(status.HTTP_409_CONFLICT, "PAYMENT_ALREADY_USED", "Bu ödeme zaten kullanılmış.")
        if payment.purpose != purpose:
            raise AppException(
                status.HTTP_400_BAD_REQUEST, "PAYMENT_PURPOSE_MISMATCH",
                "Bu ödeme farklı bir işlem için yapılmış.",
                {"expected": purpose.value, "actual": payment.purpose.value},
            )
        if expected_plan is not None and payment.plan_id != expected_plan.id:
            raise AppException(
                status.HTTP_400_BAD_REQUEST, "PAYMENT_PLAN_MISMATCH", "Ödeme, seçilen paket için yapılmamış."
            )
        return payment

    def _roll_over(self, subscription: Subscription) -> bool:
        """Dönemi bitmiş aboneliği yeniler veya sonlandırır. Değişiklik olduysa True döner."""
        changed = False
        for _ in range(_MAX_ROLLOVERS):
            if subscription.status != SubscriptionStatus.ACTIVE or as_utc(subscription.expires_at) > utcnow():
                break
            changed = True
            if not subscription.auto_renew:
                subscription.status = SubscriptionStatus.CANCELLED
                logger.info("subscription_ended id=%s", subscription.id)
                break
            self._renew(subscription)
        if changed:
            self.db.flush()
            self.db.refresh(subscription)
        return changed

    def _renew(self, subscription: Subscription) -> None:
        plan = subscription.pending_plan or subscription.plan
        last_payment = self.payments.last_successful_for_user(subscription.user_id)
        self.payments.create(
            user_id=subscription.user_id,
            plan_id=plan.id,
            purpose=PaymentPurpose.RENEWAL,
            amount=plan.monthly_price,
            status=PaymentStatus.SUCCESS,
            card_last4=last_payment.card_last4 if last_payment else "0000",
            subscription_id=subscription.id,
        )
        subscription.plan_id = plan.id
        subscription.pending_plan_id = None
        subscription.remaining_credits = plan.monthly_credits
        subscription.remaining_guest_credits = plan.guest_credits
        subscription.started_at = subscription.expires_at
        subscription.expires_at = as_utc(subscription.expires_at) + self._period()
        self.db.flush()
        self.db.refresh(subscription)
        logger.info("subscription_renewed id=%s plan=%s", subscription.id, plan.plan_type.value)

    @staticmethod
    def _resume(subscription: Subscription) -> None:
        subscription.auto_renew = True
        subscription.cancelled_at = None

    @staticmethod
    def _period() -> timedelta:
        return timedelta(days=settings.subscription_period_days)
