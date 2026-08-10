"""Kiosk pairing: one-time codes, device secrets, revocation, and cookie flags."""

from __future__ import annotations

import datetime as dt

import pytest
from django.contrib.auth.models import User
from django.test import Client, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.devices import services
from apps.devices.models import KioskDevice, PairingCode
from apps.identity.auth import services as identity_services
from apps.identity.models import Employee

pytestmark = pytest.mark.django_db


def _manager() -> User:
    return User.objects.create_user("mgr", password="a-strong-password-123456", is_staff=True)


def test_create_and_activate_once() -> None:
    code = services.create_pairing_code(_manager())
    result = services.activate_device(code, "매장 태블릿")
    assert result is not None
    assert KioskDevice.objects.count() == 1
    # The stored secret is a hash, not the cleartext handed to the device.
    assert result.device_secret not in result.device.secret_hash


def test_pairing_code_cannot_be_reused() -> None:
    code = services.create_pairing_code(_manager())
    assert services.activate_device(code, "tablet-1") is not None
    assert services.activate_device(code, "tablet-2") is None
    assert KioskDevice.objects.count() == 1


def test_expired_pairing_code_rejected() -> None:
    code = services.create_pairing_code(_manager())
    PairingCode.objects.update(expires_at=timezone.now() - dt.timedelta(minutes=1))
    assert services.activate_device(code, "tablet") is None


def test_verify_device_ok_and_wrong_secret() -> None:
    code = services.create_pairing_code(_manager())
    result = services.activate_device(code, "tablet")
    assert result is not None
    assert services.verify_device(result.device.pk, result.device_secret) is not None
    assert services.verify_device(result.device.pk, "wrong-secret") is None


def test_revoked_device_cannot_verify() -> None:
    code = services.create_pairing_code(_manager())
    result = services.activate_device(code, "tablet")
    assert result is not None
    services.revoke_device(result.device)
    assert services.verify_device(result.device.pk, result.device_secret) is None


@override_settings(KIOSK_COOKIE_NAME="__Host-kiosk", KIOSK_COOKIE_SECURE=True,
                   KIOSK_COOKIE_SAMESITE="Strict")
def test_activate_view_sets_hardened_cookie() -> None:
    code = services.create_pairing_code(_manager())
    client = Client()
    response = client.post(reverse("devices:kiosk_activate"), {"code": code})
    assert response.status_code == 200
    cookie = response.cookies["__Host-kiosk"]
    assert cookie["secure"] is True
    assert cookie["httponly"] is True
    assert cookie["samesite"] == "Strict"
    assert cookie["path"] == "/"  # host-only: no Domain attribute
    assert cookie["domain"] == ""


def test_activate_view_rejects_bad_code() -> None:
    client = Client()
    response = client.post(reverse("devices:kiosk_activate"), {"code": "deadbeef"})
    assert response.status_code == 400


@override_settings(DEBUG=True, EMPLOYEE_MASTER_PIN="246810")
def test_local_kiosk_unlock_returns_current_shift_state() -> None:
    # Given
    employee = Employee.objects.create(
        employee_code="EMP-001",
        display_name="테스트 직원",
        hire_date=dt.date(2026, 1, 1),
    )
    identity_services.set_employee_pin(employee, "123456")

    # When
    response = Client().post(
        reverse("devices:kiosk_unlock"),
        {"employee_code": "EMP-001", "pin": "246810"},
    )

    # Then
    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "employee_name": "테스트 직원",
        "shift_state": "IDLE",
    }
