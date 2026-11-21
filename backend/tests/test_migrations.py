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
