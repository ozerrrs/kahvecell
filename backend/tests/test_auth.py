from sqlalchemy import select

from app.models import User
from app.models.enums import UserRole
from app.schemas.user import normalize_phone_number
from tests.conftest import auth_header, login

import pytest


# ------------------------------------------------------------------ telefon
@pytest.mark.parametrize("raw", ["0555 123 45 67", "5551234567", "+90 555 123 45 67", "905551234567"])
def test_phone_number_is_normalized(raw):
    assert normalize_phone_number(raw) == "+905551234567"


@pytest.mark.parametrize("raw", ["", "12345", "0212 123 45 67", "0555 123 45 6"])
def test_invalid_phone_number_rejected(client, raw):
    res = client.post("/api/v1/auth/register", json={"phone_number": raw})
    assert res.status_code == 422
    body = res.json()
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"


# ---------------------------------------------------------------- kayıt akışı
def test_full_registration_flow(client):
    res = client.post("/api/v1/auth/register", json={"phone_number": "0555 111 22 33"})
    assert res.status_code == 200
    assert res.json()["data"]["is_new_user"] is True

    data = login(client)
    assert data["is_new_user"] is True  # kullanıcı ilk başarılı doğrulamada oluşturulur
    assert data["user"]["phone_number"] == "+905551112233"
    assert data["user"]["role"] == "CUSTOMER"
    assert data["user"]["profile_completed"] is False

    me = client.get("/api/v1/users/me", headers=auth_header(data["access_token"]))
    assert me.status_code == 200

    updated = client.patch(
        "/api/v1/users/me",
        headers=auth_header(data["access_token"]),
        json={"full_name": "Ayşe Yılmaz", "email": "AYSE@ornek.com",
              "preferences": {"favorite_coffees": ["Latte"], "allergens": ["laktoz"]}},
    )
    assert updated.status_code == 200
    user = updated.json()["data"]
    assert user["profile_completed"] is True
    assert user["email"] == "ayse@ornek.com"
    assert user["preferences"]["allergens"] == ["laktoz"]


def test_first_verify_marks_new_user(client):
    client.post("/api/v1/auth/register", json={"phone_number": "05559998877"})
    res = client.post("/api/v1/auth/verify-otp", json={"phone_number": "05559998877", "code": "1234"})
    assert res.json()["data"]["is_new_user"] is True


def test_returning_user_is_not_duplicated(client, db):
    login(client)
    login(client)
    users = db.scalars(select(User).where(User.phone_number == "+905551112233")).all()
    assert len(users) == 1


# ---------------------------------------------------------------------- OTP
def test_wrong_otp_rejected(client):
    client.post("/api/v1/auth/register", json={"phone_number": "05551112233"})
    res = client.post("/api/v1/auth/verify-otp", json={"phone_number": "05551112233", "code": "0000"})
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "OTP_INVALID"
    assert res.json()["error"]["details"]["remaining_attempts"] == 4


def test_verify_without_register_fails(client):
    res = client.post("/api/v1/auth/verify-otp", json={"phone_number": "05551112233", "code": "1234"})
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "OTP_EXPIRED"


def test_otp_cannot_be_reused(client):
    login(client)
    res = client.post("/api/v1/auth/verify-otp", json={"phone_number": "05551112233", "code": "1234"})
    assert res.status_code == 400


def test_too_many_attempts_locks_code(client):
    client.post("/api/v1/auth/register", json={"phone_number": "05551112233"})
    for _ in range(5):
        client.post("/api/v1/auth/verify-otp", json={"phone_number": "05551112233", "code": "0000"})
    res = client.post("/api/v1/auth/verify-otp", json={"phone_number": "05551112233", "code": "1234"})
    assert res.status_code == 429
    assert res.json()["error"]["code"] == "OTP_TOO_MANY_ATTEMPTS"


# ------------------------------------------------------------------- tokens
def test_refresh_rotates_tokens(client):
    data = login(client)
    res = client.post("/api/v1/auth/refresh", json={"refresh_token": data["refresh_token"]})
    assert res.status_code == 200
    new = res.json()["data"]
    assert new["refresh_token"] != data["refresh_token"]
    assert client.get("/api/v1/users/me", headers=auth_header(new["access_token"])).status_code == 200

    # Eski yenileme anahtarı ikinci kez kullanılamaz…
    reuse = client.post("/api/v1/auth/refresh", json={"refresh_token": data["refresh_token"]})
    assert reuse.status_code == 401
    # …ve tekrar kullanım denemesi tüm oturumları kapatır.
    after = client.post("/api/v1/auth/refresh", json={"refresh_token": new["refresh_token"]})
    assert after.status_code == 401


def test_access_token_cannot_be_used_as_refresh(client):
    data = login(client)
    res = client.post("/api/v1/auth/refresh", json={"refresh_token": data["access_token"]})
    assert res.status_code == 401


def test_logout_revokes_refresh_token(client):
    data = login(client)
    assert client.post("/api/v1/auth/logout", json={"refresh_token": data["refresh_token"]}).status_code == 200
    res = client.post("/api/v1/auth/refresh", json={"refresh_token": data["refresh_token"]})
    assert res.status_code == 401


def test_me_requires_token(client):
    res = client.get("/api/v1/users/me")
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "NOT_AUTHENTICATED"


def test_garbage_token_rejected(client):
    res = client.get("/api/v1/users/me", headers=auth_header("abc.def.ghi"))
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "INVALID_TOKEN"


# -------------------------------------------------------------------- roller
def _make_admin(db, phone="+905551112233"):
    user = db.scalar(select(User).where(User.phone_number == phone))
    user.role = UserRole.ADMIN
    db.commit()


def test_customer_cannot_access_admin(client):
    data = login(client)
    res = client.get("/api/v1/admin/users", headers=auth_header(data["access_token"]))
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "FORBIDDEN"


def test_admin_can_list_users_and_change_role(client, db):
    admin = login(client)
    _make_admin(db)
    customer = login(client, "05554443322")

    res = client.get("/api/v1/admin/users", headers=auth_header(admin["access_token"]))
    assert res.status_code == 200
    assert res.json()["data"]["total"] == 2

    res = client.patch(
        f"/api/v1/admin/users/{customer['user']['id']}/role",
        headers=auth_header(admin["access_token"]),
        json={"role": "SHOP_OWNER"},
    )
    assert res.status_code == 200
    assert res.json()["data"]["role"] == "SHOP_OWNER"


def test_role_change_takes_effect_immediately(client, db):
    """Rol token'dan değil veritabanından okunur: yetki alınınca eski token da yetkisiz kalır."""
    data = login(client)
    _make_admin(db)
    assert client.get("/api/v1/admin/users", headers=auth_header(data["access_token"])).status_code == 200
    user = db.scalar(select(User).where(User.phone_number == "+905551112233"))
    user.role = UserRole.CUSTOMER
    db.commit()
    assert client.get("/api/v1/admin/users", headers=auth_header(data["access_token"])).status_code == 403


def test_unknown_route_uses_standard_format(client):
    res = client.get("/api/v1/yok-boyle-bir-adres")
    assert res.status_code == 404
    assert res.json() == {"success": False, "data": None,
                          "error": {"code": "NOT_FOUND", "message": "Not Found", "details": None}}
