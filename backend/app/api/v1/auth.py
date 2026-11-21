from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.schemas.auth import (
    AuthResult,
    LoginRequest,
    OtpSentResponse,
    RefreshTokenRequest,
    RegisterRequest,
    TokenPair,
    VerifyOtpRequest,
)
from app.schemas.common import ApiResponse, MessageOut, ok
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=ApiResponse[OtpSentResponse], status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.auth_rate_limit)
def register(request: Request, body: RegisterRequest, db: Session = Depends(get_db)):
    """Yeni kullanıcı kaydı (telefon, ad soyad, şifre). OTP gönderildikten sonra /verify-otp ile doğrulanır.

    Şifre: en az 8 karakter, en az bir harf ve bir rakam. SMS simülasyonu: kod her zaman `1234`.
    Numara zaten kayıtlıysa **409** döner.
    """
    return ok(AuthService(db).register(body.phone_number, body.full_name, body.email, body.password))


@router.post("/login", response_model=ApiResponse[OtpSentResponse])
@limiter.limit(settings.auth_rate_limit)
def login(request: Request, body: LoginRequest, db: Session = Depends(get_db)):
    """Giriş 1. adım: telefon + şifre. Doğruysa SMS kodu gönderilir; 2. adım /verify-otp.

    Numara veya şifre hatalıysa **401** `INVALID_CREDENTIALS` (hangisinin hatalı olduğu söylenmez).
    """
    return ok(AuthService(db).login(body.phone_number, body.password))


@router.post("/verify-otp", response_model=ApiResponse[AuthResult])
@limiter.limit(settings.auth_rate_limit)
def verify_otp(request: Request, body: VerifyOtpRequest, db: Session = Depends(get_db)):
    """OTP'yi doğrular, geçerliyse access + refresh token döner.

    Kayıtta hesap bu adımda oluşturulur (`is_new_user: true`). Girişte bu adıma sadece
    şifre doğrulandıktan sonra gelinebilir.
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
