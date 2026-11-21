from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.geo import BoundingBox
from app.models import Shop


class ShopRepository:
    def __init__(self, db: Session):
        self.db = db

    def find(
        self,
        *,
        box: BoundingBox | None = None,
        search: str | None = None,
        min_rating: float | None = None,
    ) -> list[Shop]:
        """Aktif dükkânları veritabanı seviyesindeki filtrelerle getirir.

        `box` verilirse (lat, lng) index'i kullanılarak kare alan dışındakiler elenir;
        kesin mesafe filtresi servis katmanında Haversine ile yapılır.
        """
        query = select(Shop).where(Shop.is_active.is_(True))
        if box is not None:
            query = query.where(
                Shop.latitude.between(box.min_lat, box.max_lat),
                Shop.longitude.between(box.min_lng, box.max_lng),
            )
        if search:
            query = query.where(Shop.search_text.contains(search, autoescape=True))
        if min_rating is not None:
            query = query.where(Shop.rating >= Decimal(str(min_rating)))
        return list(self.db.scalars(query).all())

    def get_with_menu(self, shop_id: str) -> Shop | None:
        return self.db.scalar(
            select(Shop)
            .where(Shop.id == shop_id, Shop.is_active.is_(True))
            .options(selectinload(Shop.products))
        )
