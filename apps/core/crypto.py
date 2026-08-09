"""Application-level symmetric encryption for secrets at rest.

Used to encrypt TOTP seeds before they are written to the database. The key is
supplied by settings (``APP_ENCRYPTION_KEY``); in production it comes from the
secrets manager, and in dev it is derived deterministically from ``SECRET_KEY``
so local data round-trips without extra configuration.
"""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet
from django.conf import settings


def _fernet() -> Fernet:
    raw = getattr(settings, "APP_ENCRYPTION_KEY", "") or settings.SECRET_KEY
    # Fernet requires a 32-byte url-safe base64 key; derive one from the secret.
    digest = hashlib.sha256(raw.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode("utf-8")).decode("ascii")


def decrypt(token: str) -> str:
    return _fernet().decrypt(token.encode("ascii")).decode("utf-8")
