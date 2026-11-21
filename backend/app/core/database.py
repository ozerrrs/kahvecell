"""Veritabanı bağlantısı, oturum yönetimi ve tablo oluşturma."""

from collections.abc import Generator

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


def init_db() -> None:
    """Eksik tabloları oluşturur (var olanlara dokunmaz)."""
    from app import models  # noqa: F401  — modellerin Base'e kaydolması için

    Base.metadata.create_all(bind=engine)
