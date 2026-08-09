"""Kiosk punch endpoint: device gating and one-shot token consumption."""

from __future__ import annotations

import datetime as dt

import pytest
from django.conf import settings
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.attendance.models import PunchEvent
from apps.devices.services import activate_device, create_pairing_code
from apps.devices.views import KIOSK_ACTION_TOKEN_KEY
from apps.identity.models import Employee

pytestmark = pytest.mark.django_db


def _paired_client_with_unlock(emp_code: str) -> Client:
    manager = User.objects.create_user("mgr", password="pw-123456-strong", is_staff=True)
    result = activate_device(create_pairing_code(manager), "매장 태블릿")
    assert result is not None
    client = Client()
    client.cookies[settings.KIOSK_COOKIE_NAME] = f"{result.device.pk}:{result.device_secret}"
    session = client.session
    session[KIOSK_ACTION_TOKEN_KEY] = {
        "employee_code": emp_code,
        "expires_at": (timezone.now() + dt.timedelta(minutes=2)).isoformat(),
    }
    session.save()
    return client


def test_unpaired_device_forbidden() -> None:
    Employee.objects.create(
        employee_code="EMP-1", display_name="직원", hire_date=dt.date(2026, 1, 1)
    )
    resp = Client().post(
        reverse("attendance:kiosk_punch"), {"kind": "CLOCK_IN", "idempotency_key": "k"}
    )
    assert resp.status_code == 403


def test_punch_succeeds_then_token_is_consumed() -> None:
    Employee.objects.create(
        employee_code="EMP-1", display_name="직원", hire_date=dt.date(2026, 1, 1)
    )
    client = _paired_client_with_unlock("EMP-1")

    resp = client.post(
        reverse("attendance:kiosk_punch"), {"kind": "CLOCK_IN", "idempotency_key": "k1"}
    )
    assert resp.status_code == 200
    assert resp.json() == {"ok": True, "kind": "CLOCK_IN"}
    assert PunchEvent.objects.count() == 1

    # Token was one-shot: a second punch without a fresh unlock is locked out.
    resp2 = client.post(
        reverse("attendance:kiosk_punch"), {"kind": "CLOCK_OUT", "idempotency_key": "k2"}
    )
    assert resp2.status_code == 401
    assert PunchEvent.objects.count() == 1


def test_missing_idempotency_key_rejected() -> None:
    Employee.objects.create(
        employee_code="EMP-1", display_name="직원", hire_date=dt.date(2026, 1, 1)
    )
    client = _paired_client_with_unlock("EMP-1")
    resp = client.post(reverse("attendance:kiosk_punch"), {"kind": "CLOCK_IN"})
    assert resp.status_code == 400
