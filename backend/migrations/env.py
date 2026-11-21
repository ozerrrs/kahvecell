"""Alembic ortam dosyası: migration'ları uygulamanın ayarları ve modelleriyle çalıştırır."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app import models  # noqa: F401  — tüm tabloların Base.metadata'ya kaydolması için
from app.core.config import settings
from app.core.database import Base

config = context.config

# Veritabanı adresi alembic.ini'den değil, uygulamanın ayarlarından (.env) gelir.
config.set_main_option("sqlalchemy.url", settings.database_url)

# Komut satırından çalışınca loglamayı alembic.ini'ye göre kur; uygulama içinden çağrılınca
# uygulamanın kendi log ayarlarını bozma.
if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata

_is_sqlite = settings.database_url.startswith("sqlite")


def run_migrations_offline() -> None:
    """Veritabanına bağlanmadan SQL çıktısı üretir (alembic upgrade --sql)."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=_is_sqlite,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        if _is_sqlite:
            # SQLite'ta "batch" değişiklikler tabloyu kopyalayıp eskisini siler. Foreign key
            # kontrolü açıkken bu silme, bağlı tablolardaki satırları da (ON DELETE CASCADE)
            # siler. Migration süresince kapatıp sonunda bütünlüğü kontrol ediyoruz.
            connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
            connection.commit()  # PRAGMA'nın etkili olması için açık işlem kalmamalı
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # SQLite ALTER TABLE desteği kısıtlı; "batch" modu tabloyu kopyalayarak değiştirir.
            render_as_batch=_is_sqlite,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()
        if _is_sqlite:
            violations = connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall()
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")
            connection.commit()
            if violations:
                raise RuntimeError(f"Migration sonrası foreign key ihlali: {violations[:5]}")


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
