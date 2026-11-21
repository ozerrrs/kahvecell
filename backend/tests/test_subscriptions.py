from datetime import timedelta

import pytest
from sqlalchemy import select

from app.models import Subscription
from app.models.base import utcnow
from scripts.seed import seed_plans
from tests.conftest import auth_header, signup

OK_CARD = "4242-4242-4242-4242"
DECLINED_CARD = "4000-0000-0000-0002"


@pytest.fixture(autouse=True)
def _plans(db):
    seed_plans(db)
    db.commit()


@pytest.fixture
def headers(client):
    return auth_header(signup(client)["access_token"])


def pay(client, headers, plan_type="STARTER", card=OK_CARD, **overrides):
    body = {"plan_type": plan_type, "card_number": card, "card_holder": "Ali Yılmaz",
            "expiry": "12/30", "cvv": "123", **overrides}
    return client.post("/api/v1/payments/process", headers=headers, json=body)


def subscribe(client, headers, plan_type="STARTER") -> dict:
    txn = pay(client, headers, plan_type).json()["data"]["transaction_id"]
    res = client.post("/api/v1/subscriptions", headers=headers, json={"transaction_id": txn})
    assert res.status_code == 201, res.text
    return res.json()["data"]["subscription"]


def my_subscription(client, headers):
    return client.get("/api/v1/subscriptions/me", headers=headers)


# ------------------------------------------------------------------ paketler
def test_list_plans_is_public_and_sorted(client):
    res = client.get("/api/v1/subscriptions/plans")
    assert res.status_code == 200
    plans = res.json()["data"]
    assert [p["plan_type"] for p in plans] == ["STARTER", "PREMIUM", "UNLIMITED"]
    assert plans[0]["monthly_price"] == 89.99
    assert plans[0]["monthly_credits"] == 10
    assert plans[1]["guest_credits"] == 2
    assert plans[2]["is_unlimited"] is True and plans[2]["has_priority"] is True


# -------------------------------------------------------------------- ödeme
def test_successful_payment(client, headers):
    res = pay(client, headers)
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["success"] is True
    assert data["amount"] == 89.99
    assert data["card_last4"] == "4242"
    assert data["purpose"] == "NEW_SUBSCRIPTION"
    assert data["transaction_id"].startswith("TXN-")


def test_declined_card_is_recorded(client, headers):
    res = pay(client, headers, card=DECLINED_CARD)
    assert res.status_code == 402
    error = res.json()["error"]
    assert error["code"] == "PAYMENT_DECLINED"
    assert error["details"]["status"] == "FAILED"

    history = client.get("/api/v1/payments/me", headers=headers).json()["data"]
    assert len(history) == 1 and history[0]["status"] == "FAILED"


@pytest.mark.parametrize("field,value", [
    ("card_number", "1234 5678 9012 3456"),  # Luhn geçersiz
    ("expiry", "01/20"),                     # geçmiş tarih
    ("expiry", "13/30"),                     # geçersiz ay
    ("cvv", "12"),
])
def test_invalid_card_rejected(client, headers, field, value):
    res = pay(client, headers, **{field: value})
    assert res.status_code == 422


def test_payment_requires_login(client):
    assert pay(client, {}).status_code == 401


# ----------------------------------------------------------------- başlatma
def test_start_subscription(client, headers):
    sub = subscribe(client, headers)
    assert sub["plan"]["plan_type"] == "STARTER"
    assert sub["remaining_credits"] == 10
    assert sub["status"] == "ACTIVE"
    assert sub["auto_renew"] is True

    res = my_subscription(client, headers)
    assert res.status_code == 200
    assert res.json()["data"]["id"] == sub["id"]


def test_no_subscription_returns_404(client, headers):
    res = my_subscription(client, headers)
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "NO_ACTIVE_SUBSCRIPTION"


def test_payment_cannot_be_used_twice(client, headers):
    txn = pay(client, headers).json()["data"]["transaction_id"]
    client.post("/api/v1/subscriptions", headers=headers, json={"transaction_id": txn})
    client.delete("/api/v1/subscriptions/me", headers=headers)
    res = client.post("/api/v1/subscriptions", headers=headers, json={"transaction_id": txn})
    assert res.status_code == 409


def test_failed_payment_cannot_start_subscription(client, headers):
    txn = pay(client, headers, card=DECLINED_CARD).json()["error"]["details"]["transaction_id"]
    res = client.post("/api/v1/subscriptions", headers=headers, json={"transaction_id": txn})
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "PAYMENT_NOT_SUCCESSFUL"


def test_other_users_payment_cannot_be_used(client, headers):
    txn = pay(client, headers).json()["data"]["transaction_id"]
    other = auth_header(signup(client, "05554443322")["access_token"])
    res = client.post("/api/v1/subscriptions", headers=other, json={"transaction_id": txn})
    assert res.status_code == 404


def test_cannot_start_second_subscription(client, headers):
    subscribe(client, headers)
    res = pay(client, headers, "STARTER")
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "PAYMENT_NOT_REQUIRED"


# --------------------------------------------------------------- yükseltme
def test_upgrade_charges_difference_and_adds_credits(client, headers, db):
    subscribe(client, headers, "STARTER")
    # 3 kahve içilmiş gibi yap
    sub = db.scalar(select(Subscription))
    sub.remaining_credits = 7
    db.commit()

    payment = pay(client, headers, "PREMIUM").json()["data"]
    assert payment["purpose"] == "UPGRADE"
    assert payment["amount"] == 60.0  # 149.99 - 89.99

    res = client.patch("/api/v1/subscriptions/me", headers=headers,
                       json={"plan_type": "PREMIUM", "transaction_id": payment["transaction_id"]})
    assert res.status_code == 200
    upgraded = res.json()["data"]["subscription"]
    assert upgraded["plan"]["plan_type"] == "PREMIUM"
    assert upgraded["remaining_credits"] == 17  # 7 + (20 - 10)
    assert upgraded["remaining_guest_credits"] == 2


def test_upgrade_to_unlimited(client, headers):
    subscribe(client, headers, "PREMIUM")
    txn = pay(client, headers, "UNLIMITED").json()["data"]["transaction_id"]
    res = client.patch("/api/v1/subscriptions/me", headers=headers,
                       json={"plan_type": "UNLIMITED", "transaction_id": txn})
    sub = res.json()["data"]["subscription"]
    assert sub["remaining_credits"] is None
    assert sub["remaining_guest_credits"] == 5


def test_upgrade_without_payment_requires_payment(client, headers):
    subscribe(client, headers)
    res = client.patch("/api/v1/subscriptions/me", headers=headers, json={"plan_type": "PREMIUM"})
    assert res.status_code == 402
    assert res.json()["error"]["details"]["amount"] == 60.0


def test_upgrade_payment_must_match_plan(client, headers):
    subscribe(client, headers)
    txn = pay(client, headers, "PREMIUM").json()["data"]["transaction_id"]
    res = client.patch("/api/v1/subscriptions/me", headers=headers,
                       json={"plan_type": "UNLIMITED", "transaction_id": txn})
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "PAYMENT_PLAN_MISMATCH"


def test_new_subscription_payment_cannot_be_used_for_upgrade(client, headers):
    txn = pay(client, headers, "PREMIUM").json()["data"]["transaction_id"]  # NEW_SUBSCRIPTION ödemesi
    subscribe(client, headers, "STARTER")
    res = client.patch("/api/v1/subscriptions/me", headers=headers,
                       json={"plan_type": "PREMIUM", "transaction_id": txn})
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "PAYMENT_PURPOSE_MISMATCH"


# ---------------------------------------------------------------- düşürme
def test_downgrade_is_scheduled_for_next_period(client, headers):
    subscribe(client, headers, "PREMIUM")
    res = client.patch("/api/v1/subscriptions/me", headers=headers, json={"plan_type": "STARTER"})
    assert res.status_code == 200
    sub = res.json()["data"]["subscription"]
    assert sub["plan"]["plan_type"] == "PREMIUM"  # bu dönem değişmez
    assert sub["pending_plan"]["plan_type"] == "STARTER"
    assert sub["remaining_credits"] == 20

    renewed = client.post("/api/v1/subscriptions/me/simulate-renewal", headers=headers).json()["data"]
    assert renewed["subscription"]["plan"]["plan_type"] == "STARTER"
    assert renewed["subscription"]["remaining_credits"] == 10
    assert renewed["subscription"]["pending_plan"] is None


def test_same_plan_undoes_pending_downgrade(client, headers):
    subscribe(client, headers, "PREMIUM")
    client.patch("/api/v1/subscriptions/me", headers=headers, json={"plan_type": "STARTER"})
    res = client.patch("/api/v1/subscriptions/me", headers=headers, json={"plan_type": "PREMIUM"})
    assert res.status_code == 200
    assert res.json()["data"]["subscription"]["pending_plan"] is None


def test_same_plan_without_pending_change_is_error(client, headers):
    subscribe(client, headers)
    res = client.patch("/api/v1/subscriptions/me", headers=headers, json={"plan_type": "STARTER"})
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "SAME_PLAN"


# ------------------------------------------------------------------- iptal
def test_cancel_keeps_access_until_period_end(client, headers):
    subscribe(client, headers)
    res = client.delete("/api/v1/subscriptions/me", headers=headers)
    assert res.status_code == 200
    sub = res.json()["data"]["subscription"]
    assert sub["status"] == "ACTIVE"
    assert sub["auto_renew"] is False
    assert sub["cancelled_at"] is not None

    assert client.delete("/api/v1/subscriptions/me", headers=headers).status_code == 409

    ended = client.post("/api/v1/subscriptions/me/simulate-renewal", headers=headers).json()["data"]
    assert ended["subscription"]["status"] == "CANCELLED"
    assert my_subscription(client, headers).status_code == 404


def test_can_resubscribe_after_cancellation_ends(client, headers):
    subscribe(client, headers)
    client.delete("/api/v1/subscriptions/me", headers=headers)
    client.post("/api/v1/subscriptions/me/simulate-renewal", headers=headers)
    sub = subscribe(client, headers, "PREMIUM")
    assert sub["plan"]["plan_type"] == "PREMIUM"


# ---------------------------------------------------------------- yenileme
def test_renewal_resets_credits_and_extends_period(client, headers):
    sub = subscribe(client, headers)
    renewed = client.post("/api/v1/subscriptions/me/simulate-renewal", headers=headers).json()["data"]["subscription"]
    assert renewed["remaining_credits"] == 10
    assert renewed["expires_at"] > sub["expires_at"]

    history = client.get("/api/v1/payments/me", headers=headers).json()["data"]
    assert [p["purpose"] for p in history] == ["RENEWAL", "NEW_SUBSCRIPTION"]


def test_expired_subscription_renews_automatically_on_read(client, headers, db):
    """Dönem tarihi geçmiş abonelik, okunduğu anda otomatik yenilenir (lazy renewal)."""
    subscribe(client, headers)
    sub = db.scalar(select(Subscription))
    sub.remaining_credits = 0
    sub.expires_at = utcnow() - timedelta(minutes=1)
    db.commit()

    data = my_subscription(client, headers).json()["data"]
    assert data["remaining_credits"] == 10
