"""Test ortamı: her test boş, geçici bir veritabanıyla çalışır."""

import os
import tempfile

# Uygulama import edilmeden ÖNCE ayarlanmalı.
_tmp_dir = tempfile.mkdtemp(prefix="kahvecell-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp_dir}/test.db"
os.environ["RATE_LIMIT_ENABLED"] = "false"
# Testler her seferinde tabloları modellerden hızlıca kurar; migration'lar ayrı test edilir.
os.environ["AUTO_MIGRATE"] = "false"
os.environ["APP_ENV"] = "test"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import models  # noqa: E402,F401
from app.core.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def _fresh_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def db():
    with SessionLocal() as session:
        yield session


PASSWORD = "Kahve123"  # scripts/seed.py TEST_PASSWORD ile aynı


def register_body(phone: str = "0555 111 22 33", **extra) -> dict:
    return {"phone_number": phone, "full_name": "Ali Yılmaz", "email": "ali@example.com",
            "password": PASSWORD, **extra}


def verify(client: TestClient, phone: str, code: str = "1234"):
    return client.post("/api/v1/auth/verify-otp", json={"phone_number": phone, "code": code})


def signup(client: TestClient, phone: str = "0555 111 22 33") -> dict:
    """Yeni kullanıcı kaydı + OTP doğrulama; verify-otp yanıtının data kısmını döner."""
    res = client.post("/api/v1/auth/register", json=register_body(phone))
    assert res.status_code == 201, res.text
    res = verify(client, phone)
    assert res.status_code == 200, res.text
    return res.json()["data"]


def login(client: TestClient, phone: str = "0555 111 22 33", password: str = PASSWORD) -> dict:
    """Kayıtlı kullanıcı girişi (login: telefon + şifre → verify-otp)."""
    res = client.post("/api/v1/auth/login", json={"phone_number": phone, "password": password})
    assert res.status_code == 200, res.text
    res = verify(client, phone)
    assert res.status_code == 200, res.text
    return res.json()["data"]


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
