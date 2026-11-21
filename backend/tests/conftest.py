"""Test ortamı: her test boş, geçici bir veritabanıyla çalışır."""

import os
import tempfile

# Uygulama import edilmeden ÖNCE ayarlanmalı.
_tmp_dir = tempfile.mkdtemp(prefix="kahvecell-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp_dir}/test.db"
os.environ["RATE_LIMIT_ENABLED"] = "false"
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


def login(client: TestClient, phone: str = "0555 111 22 33") -> dict:
    """Kayıt + OTP doğrulama yapıp verify-otp yanıtının data kısmını döner."""
    assert client.post("/api/v1/auth/register", json={"phone_number": phone}).status_code == 200
    res = client.post("/api/v1/auth/verify-otp", json={"phone_number": phone, "code": "1234"})
    assert res.status_code == 200, res.text
    return res.json()["data"]


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
