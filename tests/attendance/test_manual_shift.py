from __future__ import annotations

import datetime as dt

import pytest
from django.contrib.auth.models import User
from django.db.backends.postgresql.psycopg_any import DateRange
from django.test import Client
from django.utils import timezone

from apps.attendance.models import PunchEvent, PunchKind, Shift
from apps.identity.auth.middleware import stamp_login
from apps.identity.models import Employee
from apps.payroll.models import HourlyWage
from apps.payroll.services.preview import monthly_payroll_lines

pytestmark = pytest.mark.django_db

MANUAL_URL = "/manager/attendance/manual/"


def _employee(code: str = "EMP-MANUAL") -> Employee:
    return Employee.objects.create(
        employee_code=code,
        display_name="수기 입력 직원",
        hire_date=dt.date(2026, 1, 1),
    )


def _manager_client(*, is_staff: bool = True) -> Client:
    manager = User.objects.create_user(f"manager-{is_staff}", is_staff=is_staff)
    client = Client()
    client.force_login(manager)
    session = client.session
    stamp_login(session)
    session.save()
    return client


def _payload(*, key: str = "8b98f42e-f78f-4dc9-acf6-91f1b4db91f4") -> dict[str, str]:
    return {
        "employee_code": "EMP-MANUAL",
        "started_at": "2026-08-12T09:00",
        "ended_at": "2026-08-12T17:00",
        "note": "종이 출근부 이관",
        "idempotency_key": key,
    }


def test_manual_range_creates_payable_shift() -> None:
    # Given
    employee = _employee()
    HourlyWage.objects.create(
        employee=employee,
        hourly_wage=10_000,
        effective=DateRange(dt.date(2026, 8, 1), None),
    )
    client = _manager_client()

    # When
    response = client.post(MANUAL_URL, _payload())

    # Then
    assert response.status_code == 302
    shift = Shift.objects.get(employee=employee)
    assert timezone.localtime(shift.opened_at) == timezone.make_aware(
        dt.datetime(2026, 8, 12, 9, 0)
    )
    assert timezone.localtime(shift.closed_at) == timezone.make_aware(
        dt.datetime(2026, 8, 12, 17, 0)
    )
    assert list(PunchEvent.objects.filter(shift=shift).values_list("kind", flat=True)) == [
        PunchKind.CLOCK_IN,
        PunchKind.CLOCK_OUT,
    ]
    payroll_line = monthly_payroll_lines(dt.date(2026, 8, 1))[0]
    assert payroll_line.total_hours == 8
    assert payroll_line.gross_pay == 80_000


def test_manual_range_is_idempotent() -> None:
    # Given
    _employee()
    client = _manager_client()
    payload = _payload()

    # When
    first = client.post(MANUAL_URL, payload)
    second = client.post(MANUAL_URL, payload)

    # Then
    assert first.status_code == 302
    assert second.status_code == 302
    assert Shift.objects.count() == 1
    assert PunchEvent.objects.count() == 2


def test_overlapping_manual_range_is_rejected() -> None:
    # Given
    _employee()
    client = _manager_client()
    first = client.post(MANUAL_URL, _payload())
    assert first.status_code == 302
    overlap = _payload(key="900cbd37-26b4-4e63-94b8-550ea37c94c2")
    overlap["started_at"] = "2026-08-12T16:00"
    overlap["ended_at"] = "2026-08-12T20:00"

    # When
    response = client.post(MANUAL_URL, overlap)

    # Then
    assert response.status_code == 409
    assert Shift.objects.count() == 1


def test_manual_range_requires_forward_time() -> None:
    # Given
    _employee()
    client = _manager_client()
    payload = _payload()
    payload["ended_at"] = payload["started_at"]

    # When
    response = client.post(MANUAL_URL, payload)

    # Then
    assert response.status_code == 400
    assert Shift.objects.count() == 0


def test_manual_range_requires_staff() -> None:
    # Given
    _employee()
    client = _manager_client(is_staff=False)

    # When
    response = client.post(MANUAL_URL, _payload())

    # Then
    assert response.status_code == 403
    assert Shift.objects.count() == 0
