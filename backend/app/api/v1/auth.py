from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.schemas.auth import (
    AuthResult,
    RefreshTokenRequest,
    RegisterRequest,
    RegisterResponse,
    TokenPair,
    VerifyOtpRequest,
)
from app.schemas.common import ApiResponse, MessageOut, ok
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Kimlik Doğrulama"])


@router.post("/register", response_model=ApiResponse[RegisterResponse])
@limiter.limit(settings.auth_rate_limit)
def register(request: Request, body: RegisterRequest, db: Session = Depends(get_db)):
    """**1. adım:** GSM numarasına SMS doğrulama kodu gönderir (simülasyon: kod her zaman `1234`).

    Yeni ve kayıtlı kullanıcılar için aynı adımdır — numara sistemde yoksa doğrulama sonrası hesap açılır.
    """
    return ok(AuthService(db).request_otp(body.phone_number))


@router.post("/verify-otp", response_model=ApiResponse[AuthResult])
@limiter.limit(settings.auth_rate_limit)
def verify_otp(request: Request, body: VerifyOtpRequest, db: Session = Depends(get_db)):
    """**2. adım:** Kodu doğrular; `access_token` + `refresh_token` döner.

    `user.profile_completed = false` ise uygulama profil tamamlama ekranını açmalıdır.
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
