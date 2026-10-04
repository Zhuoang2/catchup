"""Encrypt provider credentials with an instance-owned secret."""

import base64
import hashlib

from cryptography.fernet import Fernet

from catchup.errors import AppError


def _cipher(secret: str | None) -> Fernet:
    if not secret:
        raise AppError(
            "secret_not_configured",
            "Set CATCHUP_SECRET_KEY in the instance environment before saving an API key.",
        )
    key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode("utf-8")).digest())
    return Fernet(key)


def encrypt_key(api_key: str, secret: str | None) -> str:
    return _cipher(secret).encrypt(api_key.encode("utf-8")).decode("ascii")


def decrypt_key(ciphertext: str, secret: str | None) -> str:
    return _cipher(secret).decrypt(ciphertext.encode("ascii")).decode("utf-8")
