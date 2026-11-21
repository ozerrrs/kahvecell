import json
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select

from app.core import clock, qr
from app.models import Product, Shop, Subscription
from app.models.enums import UserRole
from scripts.seed import TEST_SHOP_OWNER, get_or_create_user, seed_plans, seed_shops
from tests.conftest import auth_header, login, signup

TZ = ZoneInfo("Europe/Istanbul")
OK_CARD = {"card_number": "4242-4242-4242-4242", "card_holder": "Ali", "expiry": "12/30", "cvv": "123"}
OWNER_PHONE = "05557654321"


@pytest.fixture(autouse=True)
def _world(db, monkeypatch):
    monkeypatch.setattr(clock, "local_now", lambda: datetime(2026, 11, 21, 12, 0, tzinfo=TZ))
    seed_plans(db)
    owner, _ = get_or_create_user(db, dict(TEST_SHOP_OWNER))
    seed_shops(db, owner)
    db.commit()


def subscribe(client, headers, plan="STARTER"):
    txn = client.post("/api/v1/payments/process", headers=headers,
                      json={"plan_type": plan, **OK_CARD}).json()["data"]["transaction_id"]
    assert client.post("/api/v1/subscriptions", headers=headers, json={"transaction_id": txn}).status_code == 201


@pytest.fixture
def customer(client):
    headers = auth_header(signup(client)["access_token"])
    subscribe(client, headers)
    return headers


@pytest.fixture
def owner(client):
    return auth_header(login(client, OWNER_PHONE)["access_token"])


def shop_and_product(db, shop_name="Kızılay Kavurma Evi", product_name="Latte"):
    shop = db.scalar(select(Shop).where(Shop.name == shop_name))
    product = next(p for p in shop.products if p.name == product_name)
    return shop.id, product.id


def place(client, headers, db, **extra):
    shop_id, product_id = shop_and_product(db)
    body = {"shop_id": shop_id, "product_id": product_id, "size": "L", "milk": "OAT", "sugar": 1, **extra}
    return client.post("/api/v1/orders", headers=headers, json=body)


def set_status(client, headers, order_id, status, **extra):
    return client.patch(f"/api/v1/orders/{order_id}/status", headers=headers, json={"status": status, **extra})


# ------------------------------------------------------------------ oluşturma
def test_create_order_deducts_credit_and_returns_qr(client, customer, db):
    res = place(client, customer, db, note="  az   sıcak ")
    assert res.status_code == 201, res.text
    data = res.json()["data"]
    order = data["order"]
    assert data["remaining_credits"] == 9
    assert order["status"] == "PENDING"
    assert order["next_statuses"] == ["ACCEPTED", "CANCELLED"]
    assert order["product"]["name"] == "Latte"
    assert order["size"] == "L" and order["milk"] == "OAT" and order["note"] == "az sıcak"
    assert order["credit_used"] is True
    assert [h["status"] for h in order["history"]] == ["PENDING"]

    payload = order["qr"]["payload"]
    assert list(payload) == ["order_id", "user_id", "shop_id", "created_at", "signature"]  # doküman 13.2
    assert payload["order_id"] == order["id"]
    assert payload["created_at"].endswith("Z")
    assert qr.parse_and_verify(order["qr"]["data"]) == payload


def test_order_requires_active_subscription(client, db):
    headers = auth_header(signup(client, "05554443322")["access_token"])
    res = place(client, headers, db)
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "SUBSCRIPTION_REQUIRED"


def test_order_rejected_when_credits_exhausted(client, customer, db):
    db.scalar(select(Subscription)).remaining_credits = 0
    db.commit()
    res = place(client, customer, db)
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "NO_CREDITS_LEFT"


def test_last_credit_can_be_used(client, customer, db):
    db.scalar(select(Subscription)).remaining_credits = 1
    db.commit()
    assert place(client, customer, db).json()["data"]["remaining_credits"] == 0
    assert place(client, customer, db).status_code == 403


def test_unlimited_plan_does_not_deduct(client, db):
    headers = auth_header(signup(client, "05554443322")["access_token"])
    subscribe(client, headers, "UNLIMITED")
    data = place(client, headers, db).json()["data"]
    assert data["remaining_credits"] is None
    assert data["order"]["credit_used"] is False
    assert data["order"]["is_priority"] is True


def test_product_must_belong_to_shop(client, customer, db):
    shop_id, _ = shop_and_product(db)
    _, other_product = shop_and_product(db, "Tunalı Demleme")
    res = client.post("/api/v1/orders", headers=customer, json={"shop_id": shop_id, "product_id": other_product})
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "PRODUCT_NOT_FOUND"


def test_unavailable_product_rejected(client, customer, db):
    _, product_id = shop_and_product(db)
    db.get(Product, product_id).is_available = False
    db.commit()
    assert place(client, customer, db).json()["error"]["code"] == "PRODUCT_UNAVAILABLE"


def test_closed_shop_rejected_and_no_credit_lost(client, customer, db, monkeypatch):
    monkeypatch.setattr(clock, "local_now", lambda: datetime(2026, 11, 21, 3, 0, tzinfo=TZ))
    res = place(client, customer, db)
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "SHOP_CLOSED"
    assert client.get("/api/v1/subscriptions/me", headers=customer).json()["data"]["remaining_credits"] == 10


@pytest.mark.parametrize("field,value", [("sugar", 5), ("extra_shot", 3), ("size", "XL"), ("milk", "CAMEL")])
def test_invalid_customization_rejected(client, customer, db, field, value):
    assert place(client, customer, db, **{field: value}).status_code == 422


# ------------------------------------------------------------- dükkân akışı
def test_full_shop_flow_until_delivery(client, customer, owner, db):
    order = place(client, customer, db).json()["data"]["order"]
    order_id, qr_data = order["id"], order["qr"]["data"]

    incoming = client.get("/api/v1/orders/incoming", headers=owner).json()["data"]
    assert [o["id"] for o in incoming] == [order_id]
    assert incoming[0]["qr"] is None  # dükkân QR içeriğini görmez
    assert incoming[0]["customer_name"] == "Ali Yılmaz"

    for status in ("ACCEPTED", "PREPARING", "READY"):
        res = set_status(client, owner, order_id, status)
        assert res.status_code == 200, res.text
        assert res.json()["data"]["status"] == status

    assert set_status(client, owner, order_id, "DELIVERED").json()["error"]["code"] == "QR_REQUIRED"

    res = set_status(client, owner, order_id, "DELIVERED", qr_data=qr_data)
    assert res.status_code == 200
    delivered = res.json()["data"]
    assert delivered["status"] == "DELIVERED"
    assert delivered["next_statuses"] == []
    assert [h["status"] for h in delivered["history"]] == ["PENDING", "ACCEPTED", "PREPARING", "READY", "DELIVERED"]
    assert [h["changed_by_role"] for h in delivered["history"]] == ["CUSTOMER"] + ["SHOP_OWNER"] * 4

    assert client.get("/api/v1/orders/incoming", headers=owner).json()["data"] == []  # aktif değil artık
    customer_view = client.get(f"/api/v1/orders/{order_id}", headers=customer).json()["data"]
    assert customer_view["status"] == "DELIVERED"


def test_invalid_transition_rejected(client, customer, owner, db):
    order_id = place(client, customer, db).json()["data"]["order"]["id"]
    res = set_status(client, owner, order_id, "READY")
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "INVALID_STATUS_TRANSITION"
    assert res.json()["error"]["details"]["allowed"] == ["ACCEPTED", "CANCELLED"]


def test_customer_cannot_advance_order(client, customer, db):
    order_id = place(client, customer, db).json()["data"]["order"]["id"]
    assert set_status(client, customer, order_id, "ACCEPTED").status_code == 403


def test_customer_can_cancel_pending_and_gets_credit_back(client, customer, db):
    order_id = place(client, customer, db).json()["data"]["order"]["id"]
    res = set_status(client, customer, order_id, "CANCELLED")
    assert res.status_code == 200
    assert client.get("/api/v1/subscriptions/me", headers=customer).json()["data"]["remaining_credits"] == 10


def test_customer_cannot_cancel_after_accept(client, customer, owner, db):
    order_id = place(client, customer, db).json()["data"]["order"]["id"]
    set_status(client, owner, order_id, "ACCEPTED")
    assert set_status(client, customer, order_id, "CANCELLED").status_code == 403


def test_shop_can_reject_and_credit_is_refunded(client, customer, owner, db):
    order_id = place(client, customer, db).json()["data"]["order"]["id"]
    set_status(client, owner, order_id, "ACCEPTED")
    assert set_status(client, owner, order_id, "CANCELLED").status_code == 200
    assert client.get("/api/v1/subscriptions/me", headers=customer).json()["data"]["remaining_credits"] == 10


def test_other_shop_owner_cannot_touch_order(client, customer, db):
    order_id = place(client, customer, db).json()["data"]["order"]["id"]
    other = signup(client, "05553332211")
    user = db.scalar(select(Shop).where(Shop.name == "Tunalı Demleme"))
    user.owner_id = other["user"]["id"]
    from app.models import User
    db.get(User, other["user"]["id"]).role = UserRole.SHOP_OWNER
    db.commit()
    headers = auth_header(other["access_token"])

    assert client.get(f"/api/v1/orders/{order_id}", headers=headers).status_code == 404
    assert set_status(client, headers, order_id, "ACCEPTED").status_code == 404
    assert client.get("/api/v1/orders/incoming", headers=headers).json()["data"] == []


def test_customer_cannot_see_incoming(client, customer):
    assert client.get("/api/v1/orders/incoming", headers=customer).status_code == 403


def test_other_customer_cannot_see_order(client, customer, db):
    order_id = place(client, customer, db).json()["data"]["order"]["id"]
    other = auth_header(signup(client, "05554443322")["access_token"])
    assert client.get(f"/api/v1/orders/{order_id}", headers=other).status_code == 404
    assert client.get(f"/api/v1/orders/{order_id}/qr", headers=other).status_code == 404


def test_priority_orders_first(client, customer, owner, db):
    first = place(client, customer, db).json()["data"]["order"]["id"]
    vip = auth_header(signup(client, "05554443322")["access_token"])
    subscribe(client, vip, "UNLIMITED")
    second = place(client, vip, db).json()["data"]["order"]["id"]
    incoming = client.get("/api/v1/orders/incoming", headers=owner).json()["data"]
    assert [o["id"] for o in incoming] == [second, first]


# --------------------------------------------------------------------- QR
def test_qr_image_png(client, customer, owner, db):
    order_id = place(client, customer, db).json()["data"]["order"]["id"]
    res = client.get(f"/api/v1/orders/{order_id}/qr", headers=customer)
    assert res.status_code == 200
    assert res.headers["content-type"] == "image/png"
    assert res.content.startswith(b"\x89PNG")
    assert client.get(f"/api/v1/orders/{order_id}/qr", headers=owner).status_code == 404


def test_verify_qr_genuine(client, customer, owner, db):
    order = place(client, customer, db).json()["data"]["order"]
    res = client.post("/api/v1/orders/verify-qr", headers=owner, json={"qr_data": order["qr"]["data"]})
    result = res.json()["data"]
    assert result["valid"] is True
    assert result["can_deliver"] is False
    assert result["reason"] == "QR geçerli, ancak sipariş henüz hazır değil."
    assert result["order"]["id"] == order["id"]


def test_verify_qr_when_ready(client, customer, owner, db):
    order = place(client, customer, db).json()["data"]["order"]
    for status in ("ACCEPTED", "PREPARING", "READY"):
        set_status(client, owner, order["id"], status)
    result = client.post("/api/v1/orders/verify-qr", headers=owner,
                         json={"qr_data": order["qr"]["data"]}).json()["data"]
    assert result["valid"] is True and result["can_deliver"] is True and result["reason"] is None


@pytest.mark.parametrize("tamper", [
    lambda p: {**p, "signature": "0" * 64},              # sahte imza
    lambda p: {**p, "user_id": "baskasi"},               # alan değiştirilmiş
    lambda p: {k: v for k, v in p.items() if k != "signature"},  # imza yok
])
def test_verify_qr_detects_forgery(client, customer, owner, db, tamper):
    payload = place(client, customer, db).json()["data"]["order"]["qr"]["payload"]
    forged = json.dumps(tamper(payload))
    result = client.post("/api/v1/orders/verify-qr", headers=owner, json={"qr_data": forged}).json()["data"]
    assert result["valid"] is False
    assert result["order"] is None


def test_verify_qr_garbage(client, owner):
    result = client.post("/api/v1/orders/verify-qr", headers=owner, json={"qr_data": "merhaba"}).json()["data"]
    assert result == {"valid": False, "reason": "QR kodu okunamadı.", "can_deliver": False, "order": None}


def test_qr_of_other_order_cannot_deliver(client, customer, owner, db):
    first = place(client, customer, db).json()["data"]["order"]
    second = place(client, customer, db).json()["data"]["order"]
    for status in ("ACCEPTED", "PREPARING", "READY"):
        set_status(client, owner, second["id"], status)
    res = set_status(client, owner, second["id"], "DELIVERED", qr_data=first["qr"]["data"])
    assert res.json()["error"]["code"] == "QR_MISMATCH"


def test_forged_qr_cannot_deliver(client, customer, owner, db):
    order = place(client, customer, db).json()["data"]["order"]
    for status in ("ACCEPTED", "PREPARING", "READY"):
        set_status(client, owner, order["id"], status)
    forged = json.dumps({**order["qr"]["payload"], "signature": "f" * 64})
    res = set_status(client, owner, order["id"], "DELIVERED", qr_data=forged)
    assert res.json()["error"]["code"] == "QR_INVALID"


def test_customer_cannot_verify_qr(client, customer, db):
    data = place(client, customer, db).json()["data"]["order"]["qr"]["data"]
    assert client.post("/api/v1/orders/verify-qr", headers=customer, json={"qr_data": data}).status_code == 403


# ----------------------------------------------------- geçmiş / favori / tekrar
def test_history_favorite_and_reorder(client, customer, db):
    first = place(client, customer, db).json()["data"]["order"]
    place(client, customer, db, size="S")

    history = client.get("/api/v1/orders/history", headers=customer).json()["data"]
    assert history["total"] == 2
    assert history["items"][0]["size"] == "S"  # en yeni önce

    res = client.patch(f"/api/v1/orders/{first['id']}/favorite", headers=customer, json={"is_favorite": True})
    assert res.json()["data"]["is_favorite"] is True
    favorites = client.get("/api/v1/orders/history", headers=customer, params={"favorites_only": True}).json()["data"]
    assert [o["id"] for o in favorites["items"]] == [first["id"]]

    again = client.post(f"/api/v1/orders/{first['id']}/reorder", headers=customer)
    assert again.status_code == 201
    data = again.json()["data"]
    assert data["order"]["id"] != first["id"]
    assert (data["order"]["size"], data["order"]["milk"]) == ("L", "OAT")
    assert data["remaining_credits"] == 7


def test_cannot_reorder_someone_elses_order(client, customer, db):
    order_id = place(client, customer, db).json()["data"]["order"]["id"]
    other = auth_header(signup(client, "05554443322")["access_token"])
    assert client.post(f"/api/v1/orders/{order_id}/reorder", headers=other).status_code == 404
