import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Payment
from app.models.enums import PaymentPurpose, PaymentStatus


def new_transaction_id() -> str:
    return f"TXN-{uuid.uuid4().hex[:16].upper()}"


class PaymentRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        *,
        user_id: str,
        plan_id: int,
        purpose: PaymentPurpose,
        amount: Decimal,
        status: PaymentStatus,
        card_last4: str,
        failure_reason: str | None = None,
        subscription_id: str | None = None,
    ) -> Payment:
        payment = Payment(
            user_id=user_id,
            plan_id=plan_id,
            purpose=purpose,
            amount=amount,
            status=status,
            card_last4=card_last4,
            failure_reason=failure_reason,
            subscription_id=subscription_id,
            transaction_id=new_transaction_id(),
        )
        self.db.add(payment)
        self.db.flush()
        self.db.refresh(payment)
        return payment

    def get_by_transaction_id(self, transaction_id: str) -> Payment | None:
        return self.db.scalar(select(Payment).where(Payment.transaction_id == transaction_id))

    def list_for_user(self, user_id: str, offset: int, limit: int) -> list[Payment]:
        return list(self.db.scalars(
            select(Payment)
            .where(Payment.user_id == user_id)
            .order_by(Payment.created_at.desc())
            .offset(offset)
            .limit(limit)
        ).all())

    def last_successful_for_user(self, user_id: str) -> Payment | None:
        return self.db.scalar(
            select(Payment)
            .where(Payment.user_id == user_id, Payment.status == PaymentStatus.SUCCESS)
            .order_by(Payment.created_at.desc())
            .limit(1)
        )
