from app.core.passwords import hash_password, verify_password


def test_hash_and_verify():
    stored = hash_password("Kahve123")
    assert verify_password("Kahve123", stored)
    assert not verify_password("kahve123", stored)


def test_same_password_gets_different_hashes():
    assert hash_password("Kahve123") != hash_password("Kahve123")


def test_missing_or_corrupt_hash_never_verifies():
    assert not verify_password("Kahve123", None)
    assert not verify_password("Kahve123", "")
    assert not verify_password("Kahve123", "bcrypt$bozuk")
