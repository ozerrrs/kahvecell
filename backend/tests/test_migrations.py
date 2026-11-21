"""Migration dosyalarının modellerle uyumlu olduğunu doğrular.

Bir model değiştirilip migration üretilmeyi unutulursa bu test başarısız olur.
"""

import tempfile

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect

from app.core.config import settings
from app.core.database import Base, alembic_config


def _run_against_temp_db(callback):
    original = settings.database_url
    with tempfile.TemporaryDirectory() as tmp:
        url = f"sqlite:///{tmp}/migrations.db"
        settings.database_url = url  # migrations/env.py adresi buradan okur
        try:
            return callback(url)
        finally:
            settings.database_url = original


def test_migrations_match_models():
    def check(url):
        command.upgrade(alembic_config(), "head")
        engine = create_engine(url)
        with engine.connect() as connection:
            diff = compare_metadata(
                MigrationContext.configure(connection, opts={"compare_type": True}), Base.metadata
            )
        engine.dispose()
        assert diff == [], f"Modeller ile migration'lar uyuşmuyor; yeni migration üretin: {diff}"

    _run_against_temp_db(check)


def test_downgrade_and_upgrade_keep_existing_data():
    """SQLite batch migration'ları tabloyu kopyalar; bağlı satırlar (ürünler) silinmemeli."""

    def check(url):
        config = alembic_config()
        command.upgrade(config, "head")
        engine = create_engine(url)
        with engine.begin() as conn:
            conn.exec_driver_sql("PRAGMA foreign_keys=ON")
            conn.exec_driver_sql(
                "INSERT INTO shops (id, name, address, city, latitude, longitude, opens_at, closes_at, "
                "rating, is_active, created_at, updated_at) VALUES ('s1', 'Kızılay Kahve', 'Adres', "
                "'Ankara', 39.92, 32.85, '08:00:00', '22:00:00', 4.5, 1, '2026-01-01', '2026-01-01')"
            )
            conn.exec_driver_sql(
                "INSERT INTO products (id, shop_id, name, category, base_price, is_available, created_at, "
                "updated_at) VALUES ('p1', 's1', 'Latte', 'Espresso', 170, 1, '2026-01-01', '2026-01-01')"
            )
        engine.dispose()

        command.downgrade(config, "0001")
        command.upgrade(config, "head")

        engine = create_engine(url)
        with engine.connect() as conn:
            assert conn.exec_driver_sql("SELECT count(*) FROM products").scalar() == 1
            assert conn.exec_driver_sql("SELECT version_num FROM alembic_version").scalar() == "0002"
            assert conn.exec_driver_sql("SELECT search_text FROM shops").scalar() == "kizilay kahve adres ankara"
        engine.dispose()

    _run_against_temp_db(check)


def test_migrations_can_be_rolled_back():
    def check(url):
        config = alembic_config()
        command.upgrade(config, "head")
        command.downgrade(config, "base")
        engine = create_engine(url)
        tables = set(inspect(engine).get_table_names()) - {"alembic_version"}
        engine.dispose()
        assert tables == set()

    _run_against_temp_db(check)
