"""add shop search_text

Dükkân aramasını Türkçe karakter ve büyük/küçük harften bağımsız yapmak için
ad + adres + şehrin sadeleştirilmiş halini tutan sütun. Var olan dükkânlar da doldurulur.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-21 13:23:09.461583
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, Sequence[str], None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Migration'lar uygulama kodu değişse de aynı sonucu vermeli; bu yüzden fonksiyon burada sabitlenir.
_TR_LOWER = str.maketrans({"I": "ı", "İ": "i"})
_ASCII_FOLD = str.maketrans({"ç": "c", "ğ": "g", "ı": "i", "ö": "o", "ş": "s", "ü": "u", "â": "a", "î": "i", "û": "u"})


def _fold(value: str) -> str:
    return " ".join(value.translate(_TR_LOWER).lower().translate(_ASCII_FOLD).split())


def upgrade() -> None:
    with op.batch_alter_table("shops", schema=None) as batch_op:
        batch_op.add_column(sa.Column("search_text", sa.String(length=500), nullable=True))

    # Mevcut dükkânların arama metnini doldur.
    connection = op.get_bind()
    shops = sa.table("shops", sa.column("id"), sa.column("name"), sa.column("address"),
                     sa.column("city"), sa.column("search_text"))
    for row in connection.execute(sa.select(shops.c.id, shops.c.name, shops.c.address, shops.c.city)):
        connection.execute(
            shops.update()
            .where(shops.c.id == row.id)
            .values(search_text=_fold(f"{row.name} {row.address} {row.city}"))
        )


def downgrade() -> None:
    with op.batch_alter_table("shops", schema=None) as batch_op:
        batch_op.drop_column("search_text")
