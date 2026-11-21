from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import User
from app.schemas.common import ApiResponse, ok
from app.schemas.payment import PaymentOut, PaymentProcessRequest
from app.services.payment_service import PaymentService

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/process", response_model=ApiResponse[PaymentOut])
def process_payment(body: PaymentProcessRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Mobil ödeme simülasyonu.

    | Kart | Sonuç |
    |---|---|
    | `4242-4242-4242-4242` | Her zaman başarılı |
    | `4000-0000-0000-0002` | Her zaman başarısız (**402** `PAYMENT_DECLINED`) |

    Tutar otomatik belirlenir: aboneliğiniz yoksa paket fiyatı, yükseltmede fiyat farkı.
    Dönen `transaction_id` ile **POST /subscriptions** (başlatma) veya **PATCH /subscriptions/me** (yükseltme) yapılır.
    Başarısız ödemeler de geçmişe kaydedilir.
    """
    return ok(PaymentService(db).process(user, body.plan_type, body))


@router.get("/me", response_model=ApiResponse[list[PaymentOut]])
def payment_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Ödeme geçmişi (başarılı ve başarısız, en yeni önce)."""
    return ok(PaymentService(db).history(user, (page - 1) * page_size, page_size))
