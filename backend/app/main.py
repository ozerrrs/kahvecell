"""KahveCell backend giriş noktası."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import init_db
from app.core.exceptions import register_exception_handlers
from app.core.logging import setup_logging
from app.core.rate_limit import limiter
from app.schemas.common import ok

setup_logging()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Backend açılırken eksik tabloları oluştur.
    init_db()
    yield


app = FastAPI(
    title="KahveCell API",
    description="Dijital kahve abonelik platformu",
    version="0.1.0",
    lifespan=lifespan,
)
app.state.limiter = limiter

# React geliştirme sunucusunun (Vite) backend'e istek atabilmesi için izin verilen adresler.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)
app.include_router(api_router)


@app.get("/", tags=["health"])
def root():
    """Ana sayfa: backend ayakta mı?"""
    return ok({"message": "KahveCell backend çalışıyor ☕"})
