"""Endpoint'lerde ortak kullanılan bağımlılıklar: giriş yapmış kullanıcı ve rol kontrolü."""

from collections.abc import Callable

from fastapi import Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import AppException
from app.core.security import decode_token
from app.models import User
from app.models.enums import UserRole
from app.repositories.user_repository import UserRepository

_bearer = HTTPBearer(auto_error=False, description="verify-otp'den dönen access_token")


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise AppException(status.HTTP_401_UNAUTHORIZED, "NOT_AUTHENTICATED", "Giriş yapmanız gerekiyor.")
    payload = decode_token(credentials.credentials, "access")
    user = UserRepository(db).get_by_id(payload["sub"])
    if user is None:
        raise AppException(status.HTTP_401_UNAUTHORIZED, "INVALID_TOKEN", "Kullanıcı bulunamadı.")
    return user


def require_roles(*roles: UserRole) -> Callable[..., User]:
    """Sadece belirtilen rollere izin veren bağımlılık üretir. Rol, her istekte veritabanından okunur."""

    def _checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise AppException(status.HTTP_403_FORBIDDEN, "FORBIDDEN", "Bu işlem için yetkiniz yok.")
        return user

    return _checker
