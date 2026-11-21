"""/api/v1 altındaki tüm router'ları birleştirir."""

from fastapi import APIRouter

from app.api.v1 import admin, auth, users
from app.schemas.common import ok

api_router = APIRouter(prefix="/api/v1")


@api_router.get("/health", tags=["Sağlık"])
def health():
    """Frontend ve izleme araçları için sağlık kontrolü."""
    return ok({"status": "ok"})


api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(admin.router)
