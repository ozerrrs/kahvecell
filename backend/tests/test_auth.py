import pytest
from sqlalchemy import select

from app.models import User
from app.models.enums import UserRole
from app.schemas.user import normalize_phone_number
from tests.conftest import auth_header, login, register_body, signup, verify


# ------------------------------------------------------------------ telefon
@pytest.mark.parametrize("raw", ["0555 123 45 67", "5551234567", "+90 555 123 45 67", "905551234567"])
def test_phone_number_is_normalized(raw):
    assert normalize_phone_number(raw) == "+905551234567"


@pytest.mark.parametrize("raw", ["", "12345", "0212 123 45 67", "0555 123 45 6"])
def test_invalid_phone_number_rejected(client, raw):
    res = client.post("/api/v1/auth/register", json=register_body(raw))
    assert res.status_code == 422
    body = res.json()
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"


# -------------------------------------------------------------------- kayıt
def test_register_returns_otp_info(client):
    res = client.post("/api/v1/auth/register", json=register_body())
    assert res.status_code == 201
    data = res.json()["data"]
    assert data["phone_number"] == "+905551112233"
    assert data["otp_expires_in_seconds"] == 300


def test_user_is_created_only_after_verification(client, db):
    client.post("/api/v1/auth/register", json=register_body())
    assert db.scalar(select(User).where(User.phone_number == "+905551112233")) is None

    data = verify(client, "05551112233").json()["data"]
    assert data["is_new_user"] is True
    assert data["user"]["full_name"] == "Ali Yılmaz"
    assert data["user"]["email"] == "ali@example.com"
    assert data["user"]["role"] == "CUSTOMER"
    assert data["user"]["profile_completed"] is True


def test_register_requires_full_name(client):
    res = client.post("/api/v1/auth/register", json={"phone_number": "05551112233"})
    assert res.status_code == 422
    fields = [d["field"] for d in res.json()["error"]["details"]]
    assert "full_name" in fields


@pytest.mark.parametrize("email", ["ali", "ali@", "ali@example"])
def test_register_rejects_invalid_email(client, email):
    res = client.post("/api/v1/auth/register", json=register_body(email=email))
    assert res.status_code == 422


def test_register_email_is_optional_and_normalized(client):
    client.post("/api/v1/auth/register", json=register_body(email="  ALI@Example.com "))
    assert verify(client, "05551112233").json()["data"]["user"]["email"] == "ali@example.com"

    client.post("/api/v1/auth/register",
                json={"phone_number": "05554443322", "full_name": "Veli", "password": "Kahve123"})
    assert verify(client, "05554443322").json()["data"]["user"]["email"] is None


def test_register_existing_phone_conflict(client):
    signup(client)
    res = client.post("/api/v1/auth/register", json=register_body())
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "PHONE_ALREADY_REGISTERED"


# -------------------------------------------------------------------- giriş
def test_login_existing_user(client, db):
    signup(client)
    data = login(client)
    assert data["is_new_user"] is False
    assert data["user"]["full_name"] == "Ali Yılmaz"
    users = db.scalars(select(User).where(User.phone_number == "+905551112233")).all()
    assert len(users) == 1


def test_login_wrong_password_rejected(client):
    signup(client)
    res = client.post("/api/v1/auth/login", json={"phone_number": "05551112233", "password": "Yanlis123"})
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "INVALID_CREDENTIALS"
    # Şifre yanlışken SMS kodu gönderilmemeli → verify de başarısız olur.
    assert verify(client, "05551112233").status_code == 400


def test_login_unknown_user_gets_same_error(client):
    """Kayıtlı olmayan numara ile yanlış şifre aynı hatayı verir (numara varlığı sızdırılmaz)."""
    res = client.post("/api/v1/auth/login", json={"phone_number": "05551112233", "password": "Kahve123"})
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_login_requires_otp_after_password(client):
    signup(client)
    res = client.post("/api/v1/auth/login", json={"phone_number": "05551112233", "password": "Kahve123"})
    assert res.status_code == 200
    assert "access_token" not in res.json()["data"]  # şifre tek başına oturum açmaz
    assert verify(client, "05551112233").status_code == 200


def test_old_passwordless_endpoint_is_gone(client):
    res = client.post("/api/v1/auth/request-otp", json={"phone_number": "05551112233"})
    assert res.status_code == 404


@pytest.mark.parametrize("password", ["kisa1", "sadeceharf", "12345678", ""])
def test_weak_password_rejected(client, password):
    res = client.post("/api/v1/auth/register", json=register_body(password=password))
    assert res.status_code == 422


def test_password_is_stored_hashed(client, db):
    signup(client)
    user = db.scalar(select(User).where(User.phone_number == "+905551112233"))
    assert user.password_hash.startswith("scrypt$")
    assert "Kahve123" not in user.password_hash


# ---------------------------------------------------------------------- OTP
def test_wrong_otp_rejected(client):
    client.post("/api/v1/auth/register", json=register_body())
    res = verify(client, "05551112233", "0000")
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "OTP_INVALID"
    assert res.json()["error"]["details"]["remaining_attempts"] == 4


def test_verify_without_request_fails(client):
    res = verify(client, "05551112233")
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "OTP_EXPIRED"


def test_otp_cannot_be_reused(client):
    signup(client)
    assert verify(client, "05551112233").status_code == 400


def test_too_many_attempts_locks_code(client):
    client.post("/api/v1/auth/register", json=register_body())
    for _ in range(5):
        verify(client, "05551112233", "0000")
    res = verify(client, "05551112233")
    assert res.status_code == 429
    assert res.json()["error"]["code"] == "OTP_TOO_MANY_ATTEMPTS"


# ------------------------------------------------------------------ profil
def test_update_profile_preferences(client):
    data = signup(client)
    res = client.patch(
        "/api/v1/users/me",
        headers=auth_header(data["access_token"]),
        json={"preferences": {"favorite_coffees": ["Latte"], "allergens": ["laktoz"]}},
    )
    assert res.status_code == 200
    user = res.json()["data"]
    assert user["full_name"] == "Ali Yılmaz"  # gönderilmeyen alan değişmez
    assert user["preferences"]["allergens"] == ["laktoz"]


# ------------------------------------------------------------------- tokens
def test_refresh_rotates_tokens(client):
    data = signup(client)
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
    data = signup(client)
    res = client.post("/api/v1/auth/refresh", json={"refresh_token": data["access_token"]})
    assert res.status_code == 401


def test_logout_revokes_refresh_token(client):
    data = signup(client)
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
def _set_role(db, role: UserRole, phone="+905551112233"):
    user = db.scalar(select(User).where(User.phone_number == phone))
    user.role = role
    db.commit()


def test_customer_cannot_access_admin(client):
    data = signup(client)
    res = client.get("/api/v1/admin/users", headers=auth_header(data["access_token"]))
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "FORBIDDEN"


def test_admin_can_list_users_and_change_role(client, db):
    admin = signup(client)
    _set_role(db, UserRole.ADMIN)
    customer = signup(client, "05554443322")

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
    data = signup(client)
    _set_role(db, UserRole.ADMIN)
    assert client.get("/api/v1/admin/users", headers=auth_header(data["access_token"])).status_code == 200
    _set_role(db, UserRole.CUSTOMER)
    assert client.get("/api/v1/admin/users", headers=auth_header(data["access_token"])).status_code == 403


def test_unknown_route_uses_standard_format(client):
    res = client.get("/api/v1/yok-boyle-bir-adres")
    assert res.status_code == 404
    assert res.json() == {"success": False, "data": None,
                          "error": {"code": "NOT_FOUND", "message": "Not Found", "details": None}}
