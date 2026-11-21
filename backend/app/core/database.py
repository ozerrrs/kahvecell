"""Veritabanı bağlantısı, oturum yönetimi ve tablo oluşturma."""

from collections.abc import Generator
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    """Tüm tablo modellerinin türediği temel sınıf."""


_is_sqlite = settings.database_url.startswith("sqlite")

engine = create_engine(
    settings.database_url,
    # SQLite varsayılan olarak tek thread'e izin verir; FastAPI çok thread kullanır.
    connect_args={"check_same_thread": False} if _is_sqlite else {},
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@event.listens_for(Engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
    """SQLite foreign key kontrolünü varsayılan olarak kapalı tutar; burada açıyoruz."""
    if _is_sqlite:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def get_db() -> Generator[Session, None, None]:
    """Her istek için bir veritabanı oturumu açar ve sonunda kapatır."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


BACKEND_DIR = Path(__file__).resolve().parents[2]


def alembic_config() -> Config:
    """Uygulama içinden Alembic çalıştırmak için ayar nesnesi (çalışma klasöründen bağımsız)."""
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    config.attributes["configure_logger"] = False
    return config


def init_db() -> None:
    """Veritabanını en güncel şemaya getirir (bekleyen migration'ları uygular)."""
    if settings.auto_migrate:
        command.upgrade(alembic_config(), "head")
