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

pytestmark = pytest.mark.django_db


def _manager_client() -> Client:
    manager = User.objects.create_user("payroll-manager", is_staff=True)
    client = Client()
    client.force_login(manager)
    session = client.session
    stamp_login(session)
    session.save()
    return client


def _closed_shift(employee: Employee) -> None:
    start = timezone.make_aware(dt.datetime(2026, 8, 3, 9, 0))
    end = timezone.make_aware(dt.datetime(2026, 8, 3, 17, 0))
    shift = Shift.objects.create(employee=employee, closed_at=end)
    PunchEvent.objects.create(
        shift=shift,
        kind=PunchKind.CLOCK_IN,
        occurred_at=start,
        idempotency_key="preview-in",
    )
    PunchEvent.objects.create(
        shift=shift,
        kind=PunchKind.CLOCK_OUT,
        occurred_at=end,
        idempotency_key="preview-out",
    )


def test_manager_console_shows_monthly_payroll_from_attendance() -> None:
    # Given
    employee = Employee.objects.create(
        employee_code="EMP-001", display_name="테스트 직원", hire_date=dt.date(2026, 1, 1)
    )
    HourlyWage.objects.create(
        employee=employee,
        hourly_wage=10_000,
        effective=DateRange(dt.date(2026, 8, 1), None),
    )
    _closed_shift(employee)

    # When
    response = _manager_client().get("/manager/console/?month=2026-08")

    # Then
    assert response.status_code == 200
    content = response.content.decode()
    assert 'data-payroll-row="EMP-001"' in content
    assert 'data-gross-pay="80000"' in content


def test_manager_can_set_employee_hourly_wage() -> None:
    # Given
    Employee.objects.create(
        employee_code="EMP-001", display_name="테스트 직원", hire_date=dt.date(2026, 1, 1)
    )

    # When
    response = _manager_client().post(
        "/manager/payroll/wage/",
        {"employee_code": "EMP-001", "month": "2026-08", "hourly_wage": "11000"},
    )

    # Then
    assert response.status_code == 302
    assert HourlyWage.objects.get(employee__employee_code="EMP-001").hourly_wage == 11_000


def test_manager_downloads_monthly_payroll_statements() -> None:
    # Given
    employee = Employee.objects.create(
        employee_code="EMP-001", display_name="테스트 직원", hire_date=dt.date(2026, 1, 1)
    )
    HourlyWage.objects.create(
        employee=employee,
        hourly_wage=10_000,
        effective=DateRange(dt.date(2026, 8, 1), None),
    )
    _closed_shift(employee)

    # When
    response = _manager_client().get("/manager/payroll/statements/?month=2026-08")

    # Then
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/zip"
    assert response.content.startswith(b"PK")
