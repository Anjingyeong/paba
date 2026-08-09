"""Test settings. Uses a real PostgreSQL database (never SQLite) so exclusion
constraints, transaction locks and concurrency behave as in production."""

from __future__ import annotations

from .base import *  # noqa: F403

DEBUG = False
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]

# Real PostgreSQL is mandatory; the domain relies on exclusion constraints and
# row locks that SQLite cannot express.
DATABASES["default"]["NAME"] = env("POSTGRES_DB", "paris_baguette_test")  # noqa: F405

# Cookies still secure-by-name in tests; the test client does not require TLS.
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_NAME = "sessionid"
CSRF_COOKIE_NAME = "csrftoken"

# No WhiteNoise in tests (production static concern); avoids STATIC_ROOT warnings.
MIDDLEWARE = [m for m in MIDDLEWARE if "whitenoise" not in m.lower()]  # noqa: F405
STORAGES = {**STORAGES, "staticfiles": {  # noqa: F405
    "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}}

# Faster password hashing in tests without losing Argon2 coverage where needed.
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.MD5PasswordHasher",
]
