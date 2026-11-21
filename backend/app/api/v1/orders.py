from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.database import get_db
from app.models import User
from app.models.enums import OrderStatus, UserRole
from app.schemas.common import ApiResponse, Page, ok
from app.schemas.order import (
    FavoriteUpdate,
    OrderCreate,
    OrderCreateResult,
    OrderOut,
    OrderStatusUpdate,
    QrVerifyRequest,
    QrVerifyResult,
)
from app.services.order_service import OrderService

router = APIRouter(prefix="/orders", tags=["orders"])

_shop_staff = require_roles(UserRole.SHOP_OWNER, UserRole.ADMIN)


# Not: Sabit yollar (/history, /incoming, /verify-qr) /{order_id}'den ÖNCE tanımlanmalı.

@router.post("", response_model=ApiResponse[OrderCreateResult], status_code=status.HTTP_201_CREATED)
def create_order(body: OrderCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Sipariş oluşturur, abonelik hakkından 1 düşer (Unlimited'da düşmez) ve imzalı QR üretir.

    Hatalar: `SUBSCRIPTION_REQUIRED` / `NO_CREDITS_LEFT` (403), `SHOP_CLOSED` (400),
    `SHOP_NOT_FOUND` / `PRODUCT_NOT_FOUND` (404).
    """
    return ok(OrderService(db).create(user, body))


@router.get("/history", response_model=ApiResponse[Page[OrderOut]])
def order_history(
    favorites_only: bool = False,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Sipariş geçmişim (en yeni önce). `favorites_only=true` ile sadece favoriler."""
    return ok(OrderService(db).history(user, favorites_only, page, page_size))


@router.get("/incoming", response_model=ApiResponse[list[OrderOut]])
def incoming_orders(
    shop_id: str | None = None,
    status_filter: list[OrderStatus] | None = Query(None, alias="status", description="Boşsa aktif siparişler"),
    user: User = Depends(_shop_staff),
    db: Session = Depends(get_db),
):
    """**Dükkân ekranı:** kendi dükkânıma gelen siparişler. Unlimited (öncelikli) siparişler önde, sonra en eskiler."""
    return ok(OrderService(db).incoming(user, shop_id, status_filter))


@router.post("/verify-qr", response_model=ApiResponse[QrVerifyResult])
def verify_qr(body: QrVerifyRequest, user: User = Depends(_shop_staff), db: Session = Depends(get_db)):
    """**Dükkân:** okutulan QR gerçek mi? İmzayı ve siparişi kontrol eder; durumu değiştirmez.

    Teslim etmek için: `PATCH /orders/{id}/status` → `{"status": "DELIVERED", "qr_data": "..."}`
    """
    return ok(OrderService(db).verify_qr(user, body.qr_data))


@router.get("/{order_id}", response_model=ApiResponse[OrderOut])
def get_order(order_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Sipariş detayı ve durum geçmişi. Müşteriye QR içeriği de döner; dükkân sahibine dönmez."""
    return ok(OrderService(db).get(user, order_id))


@router.get(
    "/{order_id}/qr",
    response_class=Response,
    responses={200: {"content": {"image/png": {}}, "description": "QR kod görseli"}},
)
def order_qr_image(order_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Siparişin QR kodu (PNG). Sadece siparişi veren müşteri görebilir."""
    return Response(content=OrderService(db).qr_png(user, order_id), media_type="image/png")


@router.patch("/{order_id}/status", response_model=ApiResponse[OrderOut])
def update_order_status(
    order_id: str, body: OrderStatusUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Sipariş durumunu günceller.

    | Kim | Ne yapabilir |
    |---|---|
    | Dükkân sahibi / Admin | PENDING → ACCEPTED → PREPARING → READY → DELIVERED, ya da PENDING/ACCEPTED → CANCELLED |
    | Müşteri | Sadece PENDING → CANCELLED |

    **DELIVERED** için müşterinin QR metni `qr_data` olarak gönderilmelidir. İptalde hak iade edilir.
    """
    return ok(OrderService(db).update_status(user, order_id, body.status, body.qr_data))


@router.patch("/{order_id}/favorite", response_model=ApiResponse[OrderOut])
def set_favorite(
    order_id: str, body: FavoriteUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Siparişi favorilere ekler / çıkarır."""
    return ok(OrderService(db).set_favorite(user, order_id, body.is_favorite))


@router.post("/{order_id}/reorder", response_model=ApiResponse[OrderCreateResult], status_code=status.HTTP_201_CREATED)
def reorder(order_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Geçmiş (veya favori) bir siparişi aynı seçeneklerle tekrar verir."""
    return ok(OrderService(db).reorder(user, order_id))
