from datetime import datetime, time

import pytest
from sqlalchemy import select

from app.core.geo import haversine_km
from app.core.text import fold_text
from app.models import Shop
from scripts.seed import TEST_SHOP_OWNER, get_or_create_user, seed_shops

KIZILAY = {"lat": 39.9208, "lng": 32.8541}


@pytest.fixture(autouse=True)
def _shops(db):
    owner, _ = get_or_create_user(db, dict(TEST_SHOP_OWNER))
    seed_shops(db, owner)
    db.commit()


def shops(client, **params):
    res = client.get("/api/v1/shops", params=params)
    assert res.status_code == 200, res.text
    return res.json()["data"]


# --------------------------------------------------------------- yardımcılar
def test_haversine_known_distance():
    # Kızılay → Çayyolu kuş uçuşu ~14 km
    assert 13.5 < haversine_km(39.9208, 32.8541, 39.88534, 32.69028) < 14.8


@pytest.mark.parametrize("raw,expected", [
    ("KIZILAY", "kizilay"),
    ("Kızılay", "kizilay"),
    ("İSTANBUL", "istanbul"),
    ("Çayyolu  Bahçe", "cayyolu bahce"),
])
def test_fold_text(raw, expected):
    assert fold_text(raw) == expected


@pytest.mark.parametrize("opens,closes,now,expected", [
    (time(8), time(22), time(12), True),
    (time(8), time(22), time(7, 59), False),
    (time(8), time(22), time(22), False),
    (time(8), time(0), time(23, 30), True),   # gece yarısı kapanan
    (time(18), time(2), time(1), True),       # gece yarısını geçen
    (time(18), time(2), time(3), False),
])
def test_is_open_at(opens, closes, now, expected):
    shop = Shop(opens_at=opens, closes_at=closes)
    assert shop.is_open_at(datetime.combine(datetime.today(), now)) is expected


# -------------------------------------------------------------------- liste
def test_list_all_shops_sorted_by_rating(client):
    data = shops(client)
    assert data["total"] == 5
    ratings = [s["rating"] for s in data["items"]]
    assert ratings == sorted(ratings, reverse=True)
    assert all(s["distance_km"] is None for s in data["items"])


def test_nearby_sorted_by_distance_within_radius(client):
    data = shops(client, **KIZILAY)
    names = [s["name"] for s in data["items"]]
    assert names[0] == "Kızılay Kavurma Evi"
    assert "Çayyolu Bahçe Kahve" not in names  # ~14 km, varsayılan 5 km dışında
    distances = [s["distance_km"] for s in data["items"]]
    assert distances == sorted(distances)
    assert distances[0] < 0.1
    assert all(d <= 5 for d in distances)


def test_larger_radius_includes_far_shops(client):
    data = shops(client, radius=20, **KIZILAY)
    assert data["total"] == 5
    assert data["items"][-1]["name"] == "Çayyolu Bahçe Kahve"


def test_small_radius(client):
    data = shops(client, radius=0.5, **KIZILAY)
    assert [s["name"] for s in data["items"]] == ["Kızılay Kavurma Evi"]


@pytest.mark.parametrize("q,expected", [
    ("kizilay", "Kızılay Kavurma Evi"),
    ("KIZILAY", "Kızılay Kavurma Evi"),
    ("tunalı", "Tunalı Demleme"),
    ("7. cadde", "7. Cadde Kahve Durağı"),
    ("altındağ", "Hamamönü Köşk Kahvesi"),  # adreste arama
])
def test_search_by_name_or_address(client, q, expected):
    names = [s["name"] for s in shops(client, q=q)["items"]]
    assert expected in names


def test_search_with_no_match_returns_empty(client):
    data = shops(client, q="olmayan dükkan")
    assert data == {"items": [], "total": 0, "page": 1, "page_size": 20}


def test_search_special_characters_are_literal(client):
    assert shops(client, q="%")["total"] == 0


def test_min_rating_filter(client):
    data = shops(client, min_rating=4.5)
    assert {s["name"] for s in data["items"]} == {
        "Kızılay Kavurma Evi", "Tunalı Demleme", "Çayyolu Bahçe Kahve"
    }


def test_sort_by_name(client):
    names = [s["name"] for s in shops(client, sort="name")["items"]]
    assert names == sorted(names, key=fold_text)


def test_pagination(client):
    first = shops(client, page=1, page_size=2)
    second = shops(client, page=2, page_size=2)
    assert first["total"] == 5 and len(first["items"]) == 2
    assert {s["id"] for s in first["items"]}.isdisjoint({s["id"] for s in second["items"]})


def test_open_now_filter(client, db):
    # Açılış = kapanış saati "24 saat açık" demektir; böylece test saatten bağımsız olur.
    always_open = db.scalar(select(Shop).where(Shop.name == "Tunalı Demleme"))
    always_open.opens_at = always_open.closes_at = time(0)
    db.commit()
    open_names = {s["name"] for s in shops(client, open_now="true")["items"]}
    closed_names = {s["name"] for s in shops(client, open_now="false")["items"]}
    assert "Tunalı Demleme" in open_names
    assert open_names.isdisjoint(closed_names)
    assert len(open_names | closed_names) == 5


def test_lat_without_lng_is_error(client):
    res = client.get("/api/v1/shops", params={"lat": 39.92})
    assert res.status_code == 422


def test_sort_by_distance_requires_location(client):
    res = client.get("/api/v1/shops", params={"sort": "distance"})
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "LOCATION_REQUIRED"


def test_invalid_coordinates_rejected(client):
    res = client.get("/api/v1/shops", params={"lat": 120, "lng": 32})
    assert res.status_code == 422


# ------------------------------------------------------------- detay/menü
def _shop_id(client, name):
    return next(s["id"] for s in shops(client)["items"] if s["name"] == name)


def test_shop_detail_with_menu_and_distance(client):
    shop_id = _shop_id(client, "Tunalı Demleme")
    res = client.get(f"/api/v1/shops/{shop_id}", params=KIZILAY)
    assert res.status_code == 200
    shop = res.json()["data"]
    assert shop["name"] == "Tunalı Demleme"
    assert 1 < shop["distance_km"] < 3
    assert shop["description"]
    categories = [c["category"] for c in shop["menu"]]
    assert categories == sorted(categories)
    assert sum(len(c["items"]) for c in shop["menu"]) == 8
    latte = next(p for c in shop["menu"] for p in c["items"] if p["name"] == "Latte")
    assert latte["base_price"] == 185.0


def test_menu_endpoint(client):
    shop_id = _shop_id(client, "Kızılay Kavurma Evi")
    res = client.get(f"/api/v1/shops/{shop_id}/menu")
    assert res.status_code == 200
    assert sum(len(c["items"]) for c in res.json()["data"]) == 8


def test_unknown_shop_is_404(client):
    for path in ("/api/v1/shops/yok", "/api/v1/shops/yok/menu"):
        res = client.get(path)
        assert res.status_code == 404
        assert res.json()["error"]["code"] == "SHOP_NOT_FOUND"


def test_inactive_shop_is_hidden(client, db):
    shop = db.scalar(select(Shop).where(Shop.name == "Tunalı Demleme"))
    shop.is_active = False
    db.commit()
    assert shops(client)["total"] == 4
    assert client.get(f"/api/v1/shops/{shop.id}").status_code == 404


def test_search_text_updates_when_shop_renamed(db):
    shop = db.scalar(select(Shop).where(Shop.name == "Tunalı Demleme"))
    shop.name = "Kavaklıdere Kahve"
    db.commit()
    assert "kavaklidere kahve" in shop.search_text
