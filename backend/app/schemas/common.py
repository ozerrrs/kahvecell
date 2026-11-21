"""Standart API yanıt formatı: { success, data, error }."""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


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
