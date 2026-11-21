"""Standart API yanıt formatı ({ success, data, error }) ve ortak tipler."""

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any, Generic, TypeVar

from pydantic import AfterValidator, BaseModel, PlainSerializer

from app.models.base import as_utc

T = TypeVar("T")

# Tarihler her zaman UTC saat dilimi bilgisiyle döner (SQLite bu bilgiyi saklamaz).
UtcDatetime = Annotated[datetime, AfterValidator(as_utc)]

# Para tutarları veritabanında Decimal tutulur, JSON'da sayı olarak döner (örn. 89.99).
Money = Annotated[Decimal, PlainSerializer(float, return_type=float)]


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Any | None = None


class ApiResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T | None = None
    error: ErrorDetail | None = None


def ok(data: Any) -> dict:
    """Başarılı yanıtı standart formata sarar."""
    return {"success": True, "data": data, "error": None}


class MessageOut(BaseModel):
    message: str
