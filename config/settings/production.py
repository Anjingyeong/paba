"""Production settings. Fails closed: every secret and host must be provided by
the environment, and all transport/security hardening is switched on."""

from __future__ import annotations

from .base import *  # noqa: F403

DEBUG = False

# No defaults: these MUST come from the environment (Secrets Manager in AWS).
SECRET_KEY = env("DJANGO_SECRET_KEY")  # noqa: F405
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS")  # noqa: F405

# Transport security
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
X_FRAME_OPTIONS = "DENY"

# CSRF trusted origins must be explicit in production (https scheme required).
CSRF_TRUSTED_ORIGINS = [
    f"https://{host}" for host in ALLOWED_HOSTS if host not in {"localhost", "127.0.0.1"}
]
