from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.schemas.auth import (
    AuthResult,
    OtpSentResponse,
    RefreshTokenRequest,
    RegisterRequest,
    RequestOtpRequest,
    TokenPair,
    VerifyOtpRequest,
)
from app.schemas.common import ApiResponse, MessageOut, ok
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=ApiResponse[OtpSentResponse], status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.auth_rate_limit)
def register(request: Request, body: RegisterRequest, db: Session = Depends(get_db)):
    """Yeni kullanıcı kaydı. OTP gönderildikten sonra /verify-otp ile doğrulanır.

    SMS simülasyonu: kod her zaman `1234`. Numara zaten kayıtlıysa **409** döner.
    """
    return ok(AuthService(db).register(body.phone_number, body.full_name, body.email))


@router.post("/request-otp", response_model=ApiResponse[OtpSentResponse])
@limiter.limit(settings.auth_rate_limit)
def request_otp(request: Request, body: RequestOtpRequest, db: Session = Depends(get_db)):
    """Kayıtlı kullanıcı için giriş kodu gönderir. Ardından /verify-otp ile doğrulanır.

    Numara kayıtlı değilse **404** döner.
    """
    return ok(AuthService(db).request_login_otp(body.phone_number))


@router.post("/verify-otp", response_model=ApiResponse[AuthResult])
@limiter.limit(settings.auth_rate_limit)
def verify_otp(request: Request, body: VerifyOtpRequest, db: Session = Depends(get_db)):
    """OTP'yi doğrular, geçerliyse access + refresh token döner.

    Kayıt akışında hesap bu adımda oluşturulur (`is_new_user: true`).
    """
    return ok(AuthService(db).verify_otp(body.phone_number, body.code))


@router.post("/refresh", response_model=ApiResponse[TokenPair])
@limiter.limit(settings.auth_rate_limit)
def refresh(request: Request, body: RefreshTokenRequest, db: Session = Depends(get_db)):
    """Süresi dolan erişim anahtarını, kullanıcıya bir şey sormadan yeniler.

    Her yenileme anahtarı **tek kullanımlıktır**; kullanıldığında yerine yenisi verilir.
    """
    return ok(AuthService(db).refresh(body.refresh_token))


@router.post("/logout", response_model=ApiResponse[MessageOut], status_code=status.HTTP_200_OK)
def logout(body: RefreshTokenRequest, db: Session = Depends(get_db)):
    """Yenileme anahtarını iptal eder (bu cihazdan çıkış)."""
    AuthService(db).logout(body.refresh_token)
    return ok(MessageOut(message="Çıkış yapıldı."))
