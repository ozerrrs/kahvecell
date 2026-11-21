from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import AppException
from app.schemas.common import ApiResponse, Page, ok
from app.schemas.shop import MenuCategory, ShopDetail, ShopSort, ShopSummary
from app.services.shop_service import Location, ShopQuery, ShopService

router = APIRouter(prefix="/shops", tags=["shops"])


def _location(lat: float | None, lng: float | None) -> Location | None:
    if lat is None and lng is None:
        return None
    if lat is None or lng is None:
        raise AppException(422, "VALIDATION_ERROR", "lat ve lng birlikte gönderilmeli.")
    return Location(lat, lng)


@router.get("", response_model=ApiResponse[Page[ShopSummary]])
def list_shops(
    lat: float | None = Query(None, ge=-90, le=90, description="Kullanıcı enlemi", examples=[39.9208]),
    lng: float | None = Query(None, ge=-180, le=180, description="Kullanıcı boylamı", examples=[32.8541]),
    radius: float | None = Query(
        None, gt=0, le=50, description="Arama yarıçapı (km). Konum verilirse varsayılan 5 km."
    ),
    q: str | None = Query(None, max_length=100, description="Ad veya adreste arama (örn. 'kizilay', 'tunalı')"),
    min_rating: float | None = Query(None, ge=0, le=5, description="En düşük puan"),
    open_now: bool | None = Query(None, description="true: sadece şu an açık olanlar"),
    sort: ShopSort | None = Query(None, description="Varsayılan: konum varsa distance, yoksa rating"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Dükkânları listeler. Giriş gerektirmez.

    - **Konumsuz:** tüm dükkânlar, puana göre.
    - **Konumlu (`lat` + `lng`):** `radius` km içindekiler, en yakından uzağa; her birinde `distance_km`.
    - Arama Türkçe karakter ve büyük/küçük harften bağımsızdır.
    """
    query = ShopQuery(
        location=_location(lat, lng), radius_km=radius, search=q, min_rating=min_rating,
        open_now=open_now, sort=sort, page=page, page_size=page_size,
    )
    return ok(ShopService(db).search(query))


@router.get("/{shop_id}", response_model=ApiResponse[ShopDetail])
def get_shop(
    shop_id: str,
    lat: float | None = Query(None, ge=-90, le=90),
    lng: float | None = Query(None, ge=-180, le=180),
    db: Session = Depends(get_db),
):
    """Dükkân detayı: bilgiler, açık/kapalı durumu, kategorilere ayrılmış menü. Konum verilirse mesafe de döner."""
    return ok(ShopService(db).get_detail(shop_id, _location(lat, lng)))


@router.get("/{shop_id}/menu", response_model=ApiResponse[list[MenuCategory]])
def get_menu(shop_id: str, db: Session = Depends(get_db)):
    """Dükkân menüsü, kategorilere göre gruplanmış."""
    return ok(ShopService(db).get_menu(shop_id))
