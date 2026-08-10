"""Manager session security: rotation, idle/absolute timeout, CSRF, cookie flags."""

from __future__ import annotations

import datetime as dt

import pyotp
import pytest
from django.contrib.auth.models import User
from django.test import Client, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.identity.auth import services
from apps.identity.auth.middleware import LAST_ACTIVITY_KEY, LOGIN_AT_KEY

pytestmark = pytest.mark.django_db

PASSWORD = "a-strong-password-123456"


def _manager() -> tuple[User, str]:
    user = User.objects.create_user("mgr", password=PASSWORD, is_staff=True)
    secret = services.provision_totp(user)
    services.confirm_totp(user, pyotp.TOTP(secret).now())
    return user, secret


def _login(client: Client, secret: str) -> None:
    client.get(reverse("auth:login"))  # seed CSRF/session
    resp = client.post(reverse("auth:login"), {"username": "mgr", "password": PASSWORD})
    assert resp.status_code == 302
    resp = client.post(reverse("auth:mfa"), {"token": pyotp.TOTP(secret).now()})
    assert resp.status_code == 302  # redirected to the manager console on success


def test_full_login_rotates_session_key() -> None:
    _user, secret = _manager()
    client = Client()
    client.get(reverse("auth:login"))
    key_before = client.session.session_key
    _login(client, secret)
    assert "_auth_user_id" in client.session
    assert client.session[LOGIN_AT_KEY]
    assert client.session.session_key != key_before  # rotated on login


def test_recovery_code_completes_login() -> None:
    user, _secret = _manager()
    codes = services.generate_recovery_codes(user)
    client = Client()
    client.get(reverse("auth:login"))
    client.post(reverse("auth:login"), {"username": "mgr", "password": PASSWORD})
    resp = client.post(reverse("auth:mfa"), {"recovery_code": codes[0]})
    assert resp.status_code == 302  # redirected to the console, logged in
    assert "_auth_user_id" in client.session


def test_mfa_required_by_default() -> None:
    # Test (and production) inherit MANAGER_MFA_REQUIRED = True from base; only
    # local dev may relax it. This guards against accidentally shipping it off.
    from django.conf import settings

    assert settings.MANAGER_MFA_REQUIRED is True


@override_settings(MANAGER_MFA_REQUIRED=False)
def test_password_alone_logs_in_when_mfa_disabled() -> None:
    user, _secret = _manager()
    client = Client()
    client.get(reverse("auth:login"))
    resp = client.post(reverse("auth:login"), {"username": "mgr", "password": PASSWORD})
    assert resp.status_code == 302  # straight to the console, no TOTP step
    assert "_auth_user_id" in client.session


def test_password_without_totp_does_not_authenticate() -> None:
    _user, _secret = _manager()
    client = Client()
    resp = client.post(reverse("auth:login"), {"username": "mgr", "password": PASSWORD})
    assert resp.status_code == 302  # moved to MFA step, not logged in
    assert "_auth_user_id" not in client.session


def test_wrong_totp_is_rejected() -> None:
    _user, _secret = _manager()
    client = Client()
    client.post(reverse("auth:login"), {"username": "mgr", "password": PASSWORD})
    resp = client.post(reverse("auth:mfa"), {"token": "000000"})
    assert resp.status_code == 401
    assert "_auth_user_id" not in client.session


def test_mfa_locks_out_after_repeated_failures() -> None:
    _user, secret = _manager()
    client = Client()
    client.post(reverse("auth:login"), {"username": "mgr", "password": PASSWORD})
    for _ in range(services.MFA_MAX_ATTEMPTS):
        assert client.post(reverse("auth:mfa"), {"token": "000000"}).status_code == 401
    # Now locked: even the correct code is refused with 429 until the window passes.
    resp = client.post(reverse("auth:mfa"), {"token": pyotp.TOTP(secret).now()})
    assert resp.status_code == 429
    assert "_auth_user_id" not in client.session


def test_csrf_required_on_login_post() -> None:
    _manager()
    csrf_client = Client(enforce_csrf_checks=True)
    resp = csrf_client.post(reverse("auth:login"), {"username": "mgr", "password": PASSWORD})
    assert resp.status_code == 403


def test_idle_timeout_logs_out() -> None:
    _user, secret = _manager()
    client = Client()
    _login(client, secret)
    session = client.session
    session[LAST_ACTIVITY_KEY] = (timezone.now() - dt.timedelta(minutes=16)).isoformat()
    session.save()
    client.get("/health/live")  # any request runs the timeout middleware
    assert "_auth_user_id" not in client.session


def test_absolute_timeout_logs_out() -> None:
    _user, secret = _manager()
    client = Client()
    _login(client, secret)
    session = client.session
    session[LOGIN_AT_KEY] = (timezone.now() - dt.timedelta(hours=9)).isoformat()
    session.save()
    client.get("/health/live")
    assert "_auth_user_id" not in client.session


@override_settings(
    SESSION_COOKIE_NAME="__Host-sessionid",
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)
def test_session_cookie_is_hardened() -> None:
    _user, secret = _manager()
    client = Client()
    client.get(reverse("auth:login"))
    client.post(reverse("auth:login"), {"username": "mgr", "password": PASSWORD})
    resp = client.post(reverse("auth:mfa"), {"token": pyotp.TOTP(secret).now()})
    cookie = resp.cookies["__Host-sessionid"]
    assert cookie["secure"] is True
    assert cookie["httponly"] is True
    assert cookie["samesite"] == "Lax"
    assert cookie["domain"] == ""  # host-only
