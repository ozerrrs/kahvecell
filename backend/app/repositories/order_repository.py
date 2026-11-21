from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, selectinload

from app.models import Order, OrderStatusEvent, Shop, Subscription
from app.models.enums import OrderStatus


class OrderRepository:
    def __init__(self, db: Session):
        self.db = db

    def _with_relations(self, query):
        # populate_existing: oturumda zaten yüklü bir sipariş varsa (örn. durum değişikliğinden hemen
        # sonra) ilişkilerini veritabanından tazele; aksi halde yeni durum geçmişi görünmez.
        return query.execution_options(populate_existing=True).options(
            selectinload(Order.shop),
            selectinload(Order.product),
            selectinload(Order.user),
            selectinload(Order.subscription).selectinload(Subscription.plan),
            selectinload(Order.events).selectinload(OrderStatusEvent.changed_by),
        )

    def get(self, order_id: str) -> Order | None:
        return self.db.scalar(self._with_relations(select(Order).where(Order.id == order_id)))

    def add(self, order: Order) -> Order:
        self.db.add(order)
        self.db.flush()
        return order

    def add_event(self, order: Order, status: OrderStatus, changed_by_id: str | None) -> None:
        self.db.add(OrderStatusEvent(order_id=order.id, status=status, changed_by_id=changed_by_id))

    def consume_credit(self, subscription_id: str) -> bool:
        """Kahve hakkından atomik olarak 1 düşer. Hak kalmadıysa False döner.

        Tek bir UPDATE ... WHERE remaining_credits > 0 kullanılır; aynı anda iki sipariş
        gelse bile hak eksiye düşmez.
        """
        result = self.db.execute(
            update(Subscription)
            .where(Subscription.id == subscription_id, Subscription.remaining_credits > 0)
            .values(remaining_credits=Subscription.remaining_credits - 1)
        )
        return result.rowcount == 1

    def refund_credit(self, subscription_id: str) -> None:
        self.db.execute(
            update(Subscription)
            .where(Subscription.id == subscription_id, Subscription.remaining_credits.is_not(None))
            .values(remaining_credits=Subscription.remaining_credits + 1)
        )

    def list_for_user(self, user_id: str, favorites_only: bool, offset: int, limit: int) -> tuple[list[Order], int]:
        query = select(Order).where(Order.user_id == user_id)
        if favorites_only:
            query = query.where(Order.is_favorite.is_(True))
        total = self.db.scalar(select(func.count()).select_from(query.subquery())) or 0
        items = self.db.scalars(
            self._with_relations(query).order_by(Order.created_at.desc()).offset(offset).limit(limit)
        ).all()
        return list(items), total

    def list_for_shops(self, shop_ids: list[str], statuses: list[OrderStatus]) -> list[Order]:
        query = select(Order).where(Order.shop_id.in_(shop_ids), Order.status.in_(statuses))
        return list(self.db.scalars(self._with_relations(query).order_by(Order.created_at)).all())

    def shop_ids_owned_by(self, user_id: str) -> list[str]:
        return list(self.db.scalars(select(Shop.id).where(Shop.owner_id == user_id)).all())

    def all_shop_ids(self) -> list[str]:
        return list(self.db.scalars(select(Shop.id)).all())
