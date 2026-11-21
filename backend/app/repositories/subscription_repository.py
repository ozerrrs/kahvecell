from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Subscription, SubscriptionPlan
from app.models.enums import PlanType, SubscriptionStatus


class SubscriptionPlanRepository:
    def __init__(self, db: Session):
        self.db = db

    def list(self) -> list[SubscriptionPlan]:
        return list(self.db.scalars(select(SubscriptionPlan).order_by(SubscriptionPlan.monthly_price)).all())

    def get_by_type(self, plan_type: PlanType) -> SubscriptionPlan | None:
        return self.db.scalar(select(SubscriptionPlan).where(SubscriptionPlan.plan_type == plan_type))


class SubscriptionRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_active_for_user(self, user_id: str) -> Subscription | None:
        return self.db.scalar(
            select(Subscription)
            .where(Subscription.user_id == user_id, Subscription.status == SubscriptionStatus.ACTIVE)
            .order_by(Subscription.created_at.desc())
            .limit(1)
        )

    def create(
        self,
        user_id: str,
        plan: SubscriptionPlan,
        started_at: datetime,
        expires_at: datetime,
    ) -> Subscription:
        subscription = Subscription(
            user_id=user_id,
            plan_id=plan.id,
            remaining_credits=plan.monthly_credits,
            remaining_guest_credits=plan.guest_credits,
            status=SubscriptionStatus.ACTIVE,
            started_at=started_at,
            expires_at=expires_at,
        )
        self.db.add(subscription)
        self.db.flush()
        self.db.refresh(subscription)
        return subscription
