"""Dükkân keşfi: yakındakiler (Haversine), arama, filtreleme, detay ve menü."""

from dataclasses import dataclass
from datetime import datetime
from itertools import groupby
from zoneinfo import ZoneInfo

from fastapi import status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AppException
from app.core.geo import bounding_box, haversine_km
from app.core.text import fold_text
from app.models import Shop
from app.repositories.shop_repository import ShopRepository
from app.schemas.common import Page
from app.schemas.shop import MenuCategory, ProductOut, ShopDetail, ShopSort, ShopSummary


@dataclass(frozen=True)
class Location:
    lat: float
    lng: float


@dataclass(frozen=True)
class ShopQuery:
    location: Location | None = None
    radius_km: float | None = None
    search: str | None = None
    min_rating: float | None = None
    open_now: bool | None = None
    sort: ShopSort | None = None
    page: int = 1
    page_size: int = 20


class ShopService:
    def __init__(self, db: Session):
        self.shops = ShopRepository(db)

    def search(self, query: ShopQuery, now: datetime | None = None) -> Page[ShopSummary]:
        now = now or self._local_now()
        sort = query.sort or (ShopSort.DISTANCE if query.location else ShopSort.RATING)
        if sort == ShopSort.DISTANCE and query.location is None:
            raise AppException(
                status.HTTP_400_BAD_REQUEST, "LOCATION_REQUIRED", "Mesafeye göre sıralama için lat ve lng gerekli."
            )

        radius = query.radius_km or settings.default_search_radius_km
        box = bounding_box(query.location.lat, query.location.lng, radius) if query.location else None
        candidates = self.shops.find(
            box=box,
            search=fold_text(query.search) or None,
            min_rating=query.min_rating,
        )

        results: list[ShopSummary] = []
        for shop in candidates:
            distance = self._distance(shop, query.location)
            if distance is not None and distance > radius:
                continue  # kare alanın köşelerinde kalan, dairenin dışındaki dükkânlar
            summary = self._summary(shop, distance, now)
            if query.open_now is not None and summary.is_open_now != query.open_now:
                continue
            results.append(summary)

        results.sort(key=self._sort_key(sort))
        start = (query.page - 1) * query.page_size
        return Page(
            items=results[start:start + query.page_size],
            total=len(results),
            page=query.page,
            page_size=query.page_size,
        )

    def get_detail(self, shop_id: str, location: Location | None = None) -> ShopDetail:
        shop = self._get_or_404(shop_id)
        summary = self._summary(shop, self._distance(shop, location), self._local_now())
        return ShopDetail(**summary.model_dump(), description=shop.description, menu=self._menu(shop))

    def get_menu(self, shop_id: str) -> list[MenuCategory]:
        return self._menu(self._get_or_404(shop_id))

    # ---------------------------------------------------------------- yardımcı
    def _get_or_404(self, shop_id: str) -> Shop:
        shop = self.shops.get_with_menu(shop_id)
        if shop is None:
            raise AppException(status.HTTP_404_NOT_FOUND, "SHOP_NOT_FOUND", "Dükkân bulunamadı.")
        return shop

    @staticmethod
    def _menu(shop: Shop) -> list[MenuCategory]:
        # products ilişkisi (kategori, ad) sırasıyla yüklenir.
        return [
            MenuCategory(category=category, items=[ProductOut.model_validate(p) for p in items])
            for category, items in groupby(shop.products, key=lambda p: p.category)
        ]

    @staticmethod
    def _distance(shop: Shop, location: Location | None) -> float | None:
        if location is None:
            return None
        return round(haversine_km(location.lat, location.lng, shop.latitude, shop.longitude), 2)

    @staticmethod
    def _summary(shop: Shop, distance: float | None, now: datetime) -> ShopSummary:
        return ShopSummary(
            id=shop.id,
            name=shop.name,
            address=shop.address,
            city=shop.city,
            latitude=shop.latitude,
            longitude=shop.longitude,
            rating=float(shop.rating),
            photo_url=shop.photo_url,
            opens_at=shop.opens_at,
            closes_at=shop.closes_at,
            is_open_now=shop.is_open_at(now),
            distance_km=distance,
        )

    @staticmethod
    def _sort_key(sort: ShopSort):
        if sort == ShopSort.DISTANCE:
            return lambda s: (s.distance_km, s.name)
        if sort == ShopSort.NAME:
            return lambda s: fold_text(s.name)
        return lambda s: (-s.rating, s.distance_km if s.distance_km is not None else 0, s.name)

    @staticmethod
    def _local_now() -> datetime:
        return datetime.now(ZoneInfo(settings.shop_timezone))
