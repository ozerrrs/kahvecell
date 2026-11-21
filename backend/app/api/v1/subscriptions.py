from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import AppException
from app.models import User
from app.schemas.common import ApiResponse, ok
from app.schemas.subscription import (
    ChangePlanRequest,
    PlanOut,
    StartSubscriptionRequest,
    SubscriptionActionResult,
    SubscriptionOut,
)
from app.services.subscription_service import SubscriptionService

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


def _result(subscription, message: str) -> dict:
    return ok(SubscriptionActionResult(message=message, subscription=SubscriptionOut.model_validate(subscription)))


@router.get("/plans", response_model=ApiResponse[list[PlanOut]])
def list_plans(db: Session = Depends(get_db)):
    """Mevcut abonelik paketlerini listeler (giriş gerektirmez)."""
    return ok([PlanOut.model_validate(p) for p in SubscriptionService(db).list_plans()])


@router.post("", response_model=ApiResponse[SubscriptionActionResult], status_code=status.HTTP_201_CREATED)
def start_subscription(
    body: StartSubscriptionRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Abonelik başlatır. Önce **/payments/process** ile ödeme yapılır, dönen `transaction_id` buraya verilir."""
    subscription = SubscriptionService(db).start(user, body.transaction_id)
    return _result(subscription, f"{subscription.plan.name} aboneliğiniz başladı.")


@router.get("/me", response_model=ApiResponse[SubscriptionOut])
def get_my_subscription(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Aktif abonelik: paket, kalan kahve hakkı, dönem sonu. Aktif abonelik yoksa **404**."""
    return ok(SubscriptionOut.model_validate(SubscriptionService(db).get_active_or_404(user)))


@router.patch("/me", response_model=ApiResponse[SubscriptionActionResult])
def change_plan(body: ChangePlanRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Paket yükseltme / düşürme.

    - **Yükseltme:** önce /payments/process ile fark ödemesi yapılır, `transaction_id` gönderilir. Haklar hemen eklenir.
    - **Düşürme:** ücretsizdir, `transaction_id` gerekmez. Dönem sonunda uygulanır.
    - **Mevcut paketi göndermek:** bekleyen düşürmeyi veya iptali geri alır.
    """
    subscription, message = SubscriptionService(db).change_plan(user, body.plan_type, body.transaction_id)
    return _result(subscription, message)


@router.delete("/me", response_model=ApiResponse[SubscriptionActionResult])
def cancel_subscription(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Aboneliği iptal eder. Dönem sonuna kadar kullanılabilir, sonra yenilenmez."""
    subscription = SubscriptionService(db).cancel(user)
    return _result(subscription, "Aboneliğiniz iptal edildi; dönem sonuna kadar kullanabilirsiniz.")


@router.post("/me/simulate-renewal", response_model=ApiResponse[SubscriptionActionResult])
def simulate_renewal(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """**Demo:** Ay sonunu simüle eder. Haklar yenilenir, bekleyen düşürme uygulanır, iptal edildiyse sona erer.

    Üretim (production) ortamında kapalıdır.
    """
    if not settings.demo_endpoints_enabled:
        raise AppException(status.HTTP_404_NOT_FOUND, "NOT_FOUND", "Not Found")
    subscription = SubscriptionService(db).simulate_period_end(user)
    message = (
        "Dönem yenilendi." if subscription.status.value == "ACTIVE" else "Abonelik dönem sonunda sona erdi."
    )
    return _result(subscription, message)
