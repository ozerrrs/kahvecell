"""Sipariş iş kuralları: oluşturma, hak düşme, QR, durum makinesi, teslim ve geçmiş.

Durum makinesi:

    PENDING ──► ACCEPTED ──► PREPARING ──► READY ──► DELIVERED (QR okutularak)
       │            │
       └────────────┴──► CANCELLED (hak iade edilir)

- Dükkân sahibi (kendi dükkânı) ve admin tüm geçişleri yapabilir.
- Müşteri sadece PENDING durumundaki kendi siparişini iptal edebilir.
"""

import logging

from fastapi import status
from sqlalchemy.orm import Session

from app.core import clock, qr
from app.core.exceptions import AppException
from app.models import Order, Shop, User
from app.models.enums import OrderStatus, SubscriptionStatus, UserRole
from app.repositories.order_repository import OrderRepository
from app.repositories.shop_repository import ShopRepository
from app.schemas.common import Page
from app.schemas.order import (
    OrderCreate,
    OrderCreateResult,
    OrderOut,
    OrderProductOut,
    OrderQr,
    OrderShopOut,
    QrPayload,
    QrVerifyResult,
    StatusEventOut,
)
from app.services.subscription_service import SubscriptionService

logger = logging.getLogger("kahvecell.orders")

TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PENDING: {OrderStatus.ACCEPTED, OrderStatus.CANCELLED},
    OrderStatus.ACCEPTED: {OrderStatus.PREPARING, OrderStatus.CANCELLED},
    OrderStatus.PREPARING: {OrderStatus.READY},
    OrderStatus.READY: {OrderStatus.DELIVERED},
    OrderStatus.DELIVERED: set(),
    OrderStatus.CANCELLED: set(),
}
ACTIVE_STATUSES = [OrderStatus.PENDING, OrderStatus.ACCEPTED, OrderStatus.PREPARING, OrderStatus.READY]
_STATUS_ORDER = list(OrderStatus)


def _not_found() -> AppException:
    return AppException(status.HTTP_404_NOT_FOUND, "ORDER_NOT_FOUND", "Sipariş bulunamadı.")


class OrderService:
    def __init__(self, db: Session):
        self.db = db
        self.orders = OrderRepository(db)
        self.shops = ShopRepository(db)
        self.subscriptions = SubscriptionService(db)

    # ------------------------------------------------------------ oluşturma
    def create(self, user: User, data: OrderCreate) -> OrderCreateResult:
        shop = self.shops.get_with_menu(data.shop_id)
        if shop is None:
            raise AppException(status.HTTP_404_NOT_FOUND, "SHOP_NOT_FOUND", "Dükkân bulunamadı.")
        if not shop.is_open_at(clock.local_now()):
            raise AppException(
                status.HTTP_400_BAD_REQUEST, "SHOP_CLOSED",
                f"{shop.name} şu an kapalı. Çalışma saatleri: "
                f"{shop.opens_at:%H:%M}–{shop.closes_at:%H:%M}.",
            )
        product = next((p for p in shop.products if p.id == data.product_id), None)
        if product is None:
            raise AppException(status.HTTP_404_NOT_FOUND, "PRODUCT_NOT_FOUND", "Ürün bu dükkânın menüsünde yok.")
        if not product.is_available:
            raise AppException(status.HTTP_400_BAD_REQUEST, "PRODUCT_UNAVAILABLE", "Bu ürün şu an tükendi.")

        subscription = self.subscriptions.get_active(user)
        if subscription is None:
            raise AppException(
                status.HTTP_403_FORBIDDEN, "SUBSCRIPTION_REQUIRED",
                "Sipariş verebilmek için aktif bir aboneliğiniz olmalı. Paketleri inceleyin: /subscriptions/plans.",
            )
        credit_used = subscription.remaining_credits is not None
        if credit_used and not self.orders.consume_credit(subscription.id):
            raise AppException(
                status.HTTP_403_FORBIDDEN, "NO_CREDITS_LEFT",
                "Bu dönem için kahve hakkınız bitti. Paketinizi yükseltebilir veya yenilenmeyi bekleyebilirsiniz.",
                {"renews_at": subscription.expires_at.isoformat()},
            )

        order = self.orders.add(Order(
            user_id=user.id, shop_id=shop.id, product_id=product.id, subscription_id=subscription.id,
            credit_used=credit_used, size=data.size, milk=data.milk, sugar=data.sugar,
            extra_shot=data.extra_shot, note=data.note, status=OrderStatus.PENDING,
        ))
        order.qr_signature = qr.build_payload(order.id, user.id, shop.id, order.created_at)["signature"]
        self.orders.add_event(order, OrderStatus.PENDING, user.id)
        self.db.commit()
        self.db.refresh(subscription)
        logger.info("order_created order_id=%s user_id=%s shop_id=%s credit_used=%s",
                    order.id, user.id, shop.id, credit_used)
        return OrderCreateResult(
            order=self._to_out(self._load(order.id), viewer=user),
            remaining_credits=subscription.remaining_credits,
        )

    def reorder(self, user: User, order_id: str) -> OrderCreateResult:
        """Geçmiş bir siparişi aynı seçeneklerle tekrar verir (yeni hak düşer)."""
        previous = self._load(order_id)
        if previous.user_id != user.id:
            raise _not_found()
        return self.create(user, OrderCreate(
            shop_id=previous.shop_id, product_id=previous.product_id, size=previous.size,
            milk=previous.milk, sugar=previous.sugar, extra_shot=previous.extra_shot, note=previous.note,
        ))

    # -------------------------------------------------------------- okuma
    def get(self, user: User, order_id: str) -> OrderOut:
        order = self._load(order_id)
        if not (order.user_id == user.id or self._is_staff(user, order.shop)):
            raise _not_found()  # başkasının siparişinin varlığını bile belli etme
        return self._to_out(order, viewer=user)

    def qr_png(self, user: User, order_id: str) -> bytes:
        order = self._load(order_id)
        if order.user_id != user.id:
            raise _not_found()
        return qr.render_png(qr.encode(self._qr_payload(order)))

    def history(self, user: User, favorites_only: bool, page: int, page_size: int) -> Page[OrderOut]:
        items, total = self.orders.list_for_user(user.id, favorites_only, (page - 1) * page_size, page_size)
        return Page(items=[self._to_out(o, viewer=user) for o in items], total=total, page=page, page_size=page_size)

    def incoming(self, user: User, shop_id: str | None, statuses: list[OrderStatus] | None) -> list[OrderOut]:
        """Dükkân ekranı: kendi dükkân(lar)ının siparişleri. Öncelikli (Unlimited) siparişler önde, sonra en eskiler."""
        shop_ids = self.orders.all_shop_ids() if user.role == UserRole.ADMIN else self.orders.shop_ids_owned_by(user.id)
        if shop_id is not None:
            if shop_id not in shop_ids:
                raise AppException(status.HTTP_404_NOT_FOUND, "SHOP_NOT_FOUND", "Dükkân bulunamadı.")
            shop_ids = [shop_id]
        orders = self.orders.list_for_shops(shop_ids, statuses or ACTIVE_STATUSES)
        orders.sort(key=lambda o: (not o.subscription.plan.has_priority, o.created_at))
        return [self._to_out(o, viewer=user) for o in orders]

    # --------------------------------------------------------- durum değişimi
    def update_status(self, user: User, order_id: str, new_status: OrderStatus, qr_data: str | None) -> OrderOut:
        order = self._load(order_id)
        is_staff = self._is_staff(user, order.shop)
        is_customer = order.user_id == user.id
        if not (is_staff or is_customer):
            raise _not_found()

        allowed = TRANSITIONS[order.status]
        if new_status not in allowed:
            raise AppException(
                status.HTTP_409_CONFLICT, "INVALID_STATUS_TRANSITION",
                f"Sipariş {order.status.value} durumundan {new_status.value} durumuna geçemez.",
                {"current": order.status.value, "allowed": sorted(s.value for s in allowed)},
            )
        if not is_staff and not (new_status == OrderStatus.CANCELLED and order.status == OrderStatus.PENDING):
            raise AppException(
                status.HTTP_403_FORBIDDEN, "FORBIDDEN",
                "Müşteri sadece henüz kabul edilmemiş siparişini iptal edebilir.",
            )
        if new_status == OrderStatus.DELIVERED:
            self._require_matching_qr(order, qr_data)

        if new_status == OrderStatus.CANCELLED and order.credit_used \
                and order.subscription.status == SubscriptionStatus.ACTIVE:
            self.orders.refund_credit(order.subscription_id)

        order.status = new_status
        self.orders.add_event(order, new_status, user.id)
        self.db.commit()
        logger.info("order_status_changed order_id=%s status=%s by=%s", order.id, new_status.value, user.id)
        return self._to_out(self._load(order.id), viewer=user)

    def verify_qr(self, user: User, qr_data: str) -> QrVerifyResult:
        """Dükkânın okuttuğu QR gerçek mi? Durumu değiştirmez; teslim için PATCH .../status kullanılır."""
        try:
            payload = qr.parse_and_verify(qr_data)
        except qr.InvalidQr as exc:
            logger.warning("qr_rejected by=%s reason=%s", user.id, exc)
            return QrVerifyResult(valid=False, reason=str(exc))

        order = self.orders.get(payload["order_id"])
        if order is None or not self._payload_matches(order, payload):
            return QrVerifyResult(valid=False, reason="QR koduna ait sipariş bulunamadı.")
        if not self._is_staff(user, order.shop):
            return QrVerifyResult(valid=False, reason="Bu sipariş sizin dükkânınıza ait değil.")

        reason = None
        if order.status == OrderStatus.DELIVERED:
            reason = "Bu sipariş zaten teslim edilmiş."
        elif order.status == OrderStatus.CANCELLED:
            reason = "Bu sipariş iptal edilmiş."
        elif order.status != OrderStatus.READY:
            reason = "QR geçerli, ancak sipariş henüz hazır değil."
        return QrVerifyResult(
            valid=True, reason=reason, can_deliver=order.status == OrderStatus.READY,
            order=self._to_out(order, viewer=user),
        )

    def set_favorite(self, user: User, order_id: str, is_favorite: bool) -> OrderOut:
        order = self._load(order_id)
        if order.user_id != user.id:
            raise _not_found()
        order.is_favorite = is_favorite
        self.db.commit()
        return self._to_out(self._load(order.id), viewer=user)

    # ------------------------------------------------------------- yardımcı
    def _load(self, order_id: str) -> Order:
        order = self.orders.get(order_id)
        if order is None:
            raise _not_found()
        return order

    @staticmethod
    def _is_staff(user: User, shop: Shop) -> bool:
        return user.role == UserRole.ADMIN or (user.role == UserRole.SHOP_OWNER and shop.owner_id == user.id)

    @staticmethod
    def _qr_payload(order: Order) -> dict:
        return qr.build_payload(order.id, order.user_id, order.shop_id, order.created_at)

    def _payload_matches(self, order: Order, payload: dict) -> bool:
        expected = self._qr_payload(order)
        return all(expected[field] == payload[field] for field in (*qr.SIGNED_FIELDS, "signature"))

    def _require_matching_qr(self, order: Order, qr_data: str | None) -> None:
        if not qr_data:
            raise AppException(
                status.HTTP_400_BAD_REQUEST, "QR_REQUIRED",
                "Teslim için müşterinin QR kodu okutulmalı (qr_data).",
            )
        try:
            payload = qr.parse_and_verify(qr_data)
        except qr.InvalidQr as exc:
            raise AppException(status.HTTP_400_BAD_REQUEST, "QR_INVALID", str(exc))
        if not self._payload_matches(order, payload):
            raise AppException(status.HTTP_400_BAD_REQUEST, "QR_MISMATCH", "QR kodu bu siparişe ait değil.")

    def _to_out(self, order: Order, viewer: User) -> OrderOut:
        payload = self._qr_payload(order)
        order_qr = None
        if viewer.id == order.user_id:
            order_qr = OrderQr(
                payload=QrPayload(**payload),
                data=qr.encode(payload),
                image_url=f"/api/v1/orders/{order.id}/qr",
            )
        next_statuses = sorted(TRANSITIONS[order.status], key=_STATUS_ORDER.index)
        return OrderOut(
            id=order.id,
            status=order.status,
            next_statuses=next_statuses,
            shop=OrderShopOut(id=order.shop.id, name=order.shop.name, address=order.shop.address),
            product=OrderProductOut(id=order.product.id, name=order.product.name, category=order.product.category),
            size=order.size,
            milk=order.milk,
            sugar=order.sugar,
            extra_shot=order.extra_shot,
            note=order.note,
            customer_name=order.user.full_name,
            is_priority=order.subscription.plan.has_priority,
            is_favorite=order.is_favorite,
            credit_used=order.credit_used,
            created_at=order.created_at,
            updated_at=order.updated_at,
            history=[
                StatusEventOut(
                    status=e.status, changed_at=e.created_at,
                    changed_by_role=e.changed_by.role if e.changed_by else None,
                )
                for e in order.events
            ],
            qr=order_qr,
        )
