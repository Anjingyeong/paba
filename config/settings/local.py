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

# __Host- and Secure require HTTPS; drop them for plain-HTTP local dev.
KIOSK_COOKIE_NAME = "kiosk"
KIOSK_COOKIE_SECURE = False

# DEV CONVENIENCE ONLY: skip the manager TOTP step so you can log in with just a
# username + password during development. Defaults to OFF (no MFA) locally; set
# MANAGER_MFA_REQUIRED=true in your env to exercise the real TOTP flow. Never set
# in test/production — they inherit MANAGER_MFA_REQUIRED = True from base.
MANAGER_MFA_REQUIRED = env_bool("MANAGER_MFA_REQUIRED", default=False)  # noqa: F405

# DEV CONVENIENCE ONLY: common PIN for registered employees. The verification
# service additionally requires DEBUG=True, even when this value is configured.
EMPLOYEE_MASTER_PIN = env("EMPLOYEE_MASTER_PIN", "246810")  # noqa: F405
