"""Coğrafi hesaplamalar: Haversine mesafesi ve hızlı ön filtre için sınır kutusu."""

import math
from dataclasses import dataclass

EARTH_RADIUS_KM = 6371.0088


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """İki koordinat arasındaki kuş uçuşu mesafe (km). Dünyanın küreselliğini hesaba katar."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lng2 - lng1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


@dataclass(frozen=True)
class BoundingBox:
    min_lat: float
    max_lat: float
    min_lng: float
    max_lng: float


def bounding_box(lat: float, lng: float, radius_km: float) -> BoundingBox:
    """Merkez etrafında yarıçapı içine alan kare alan.

    Veritabanında (lat, lng) index'i ile ucuz bir ön eleme yapılır; kesin mesafe
    sonra Haversine ile hesaplanır.
    """
    d_lat = math.degrees(radius_km / EARTH_RADIUS_KM)
    cos_lat = max(math.cos(math.radians(lat)), 1e-6)
    d_lng = math.degrees(radius_km / (EARTH_RADIUS_KM * cos_lat))
    return BoundingBox(lat - d_lat, lat + d_lat, lng - d_lng, lng + d_lng)
