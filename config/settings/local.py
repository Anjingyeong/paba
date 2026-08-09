"""Local development settings. Relaxes secure-cookie requirements for plain HTTP."""

from __future__ import annotations

from .base import *  # noqa: F403

DEBUG = env_bool("DJANGO_DEBUG", default=True)  # noqa: F405
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")  # noqa: F405

# __Host- prefixed cookies require Secure, which needs HTTPS. On plain-HTTP dev
# we drop the prefix and the Secure flag so login works over http://localhost.
SESSION_COOKIE_NAME = "sessionid"
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_NAME = "csrftoken"
CSRF_COOKIE_SECURE = False

# WhiteNoise is a production static-serving concern; in dev the staticfiles app
# serves assets and WhiteNoise would only warn about a missing STATIC_ROOT.
MIDDLEWARE = [m for m in MIDDLEWARE if "whitenoise" not in m.lower()]  # noqa: F405
STORAGES = {**STORAGES, "staticfiles": {  # noqa: F405
    "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}}
