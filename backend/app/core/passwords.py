"""Şifre hash'leme (scrypt, Python standart kütüphanesi).

Şifreler asla düz metin saklanmaz. Her şifre için rastgele bir "tuz" (salt) üretilir;
aynı şifreyi kullanan iki kullanıcının hash'i bile farklı olur. scrypt bilerek yavaş ve
bellek yoğun bir algoritmadır; çalınan bir veritabanında şifre denemeyi pahalı kılar.

Saklama biçimi:  scrypt$<n>$<r>$<p>$<salt_b64>$<hash_b64>
"""

import base64
import hashlib
import hmac
import secrets

_N, _R, _P, _DKLEN = 2**14, 8, 1, 32

# Kullanıcı bulunamadığında da aynı süre harcansın diye (zamanlama saldırısına karşı) kullanılan sahte hash.
_DUMMY_HASH: str | None = None


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode()


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=_N, r=_R, p=_P, dklen=_DKLEN)
    return f"scrypt${_N}${_R}${_P}${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, stored: str | None) -> bool:
    """Şifre doğru mu? `stored` boşsa da (kullanıcı yok) aynı sürede False döner."""
    global _DUMMY_HASH
    if not stored:
        _DUMMY_HASH = _DUMMY_HASH or hash_password(secrets.token_hex(8))
        stored, valid_user = _DUMMY_HASH, False
    else:
        valid_user = True
    try:
        algorithm, n, r, p, salt_b64, hash_b64 = stored.split("$")
        if algorithm != "scrypt":
            return False
        expected = base64.b64decode(hash_b64)
        digest = hashlib.scrypt(
            password.encode(), salt=base64.b64decode(salt_b64),
            n=int(n), r=int(r), p=int(p), dklen=len(expected),
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(digest, expected) and valid_user
