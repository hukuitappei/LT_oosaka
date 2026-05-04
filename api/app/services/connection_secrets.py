from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings

_TOKEN_PREFIX = "fernet:v1:"


def _derive_fernet_key(raw_key: str) -> bytes:
    digest = hashlib.sha256(raw_key.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def _get_fernet() -> Fernet:
    raw_key = settings.github_connection_token_encryption_key or settings.secret_key
    return Fernet(_derive_fernet_key(raw_key))


def encrypt_github_connection_token(plaintext: str) -> str:
    if not plaintext:
        return plaintext
    token = _get_fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")
    return f"{_TOKEN_PREFIX}{token}"


def decrypt_github_connection_token(ciphertext: str | None) -> str | None:
    if ciphertext is None:
        return None
    if not ciphertext.startswith(_TOKEN_PREFIX):
        return ciphertext
    token = ciphertext.removeprefix(_TOKEN_PREFIX)
    try:
        return _get_fernet().decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Invalid encrypted GitHub connection token") from exc
