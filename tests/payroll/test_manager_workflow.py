from __future__ import annotations

import datetime as dt
import io
import zipfile

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
    assert 'data-calendar-day="2026-08-03"' in content
    assert 'data-calendar-worked="true"' in content
    assert "8.0h" in content


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


def test_manager_cannot_download_unclosed_monthly_payroll_statements() -> None:
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
    assert response.status_code == 409
    assert "월마감이 완료된 급여만" in response.content.decode()


def test_manual_week_entry_reaches_closed_payroll_statement() -> None:
    client = _manager_client()
    create = client.post(
        "/manager/employees/create/",
        {
            "employee_code": "EMP-MANUAL-E2E",
            "display_name": "수기 급여 E2E",
            "hire_date": "2026-01-01",
            "hourly_wage": "13000",
        },
    )
    assert create.status_code == 302

    entered = client.post(
        "/manager/attendance/manual-week/",
        {
            "employee_code": "EMP-MANUAL-E2E",
            "week_start": "2026-07-06",
            "batch_id": "956825f0-6cb5-4991-a674-22f807a2d124",
            "start_0": "09:00",
            "end_0": "17:00",
            "start_1": "10:00",
            "end_1": "18:30",
        },
    )
    assert entered.status_code == 302

    preview = client.get(
        "/manager/console/?month=2026-07&employee=EMP-MANUAL-E2E&week=2026-07-06"
    )
    assert preview.status_code == 200
    html = preview.content.decode()
    assert "수기 급여 E2E" in html
    assert "16.5h" in html
    assert "214500원" in html
    assert 'data-calendar-day="2026-07-06"' in html
    assert 'data-calendar-day="2026-07-07"' in html
    assert html.count('data-calendar-worked="true"') == 2
    assert "8.5h" in html

    closed = client.post(
        "/manager/payroll/close/",
        {
            "month": "2026-07",
            "pay_date": "2026-08-05",
            "reason": "7월 급여 확정",
        },
    )
    assert closed.status_code == 302

    statement = client.get("/manager/payroll/statements/?month=2026-07")
    assert statement.status_code == 200
    assert statement["Content-Type"] == "application/zip"
    with zipfile.ZipFile(io.BytesIO(statement.content)) as archive:
        names = archive.namelist()
    assert "summary-2026-07.xlsx" in names
    assert "manifest.json" in names
    assert "pay-statement-EMP-MANUAL-E2E-2026-07.xlsx" in names


def test_manager_can_prefill_week_from_previous_week_pattern() -> None:
    client = _manager_client()
    create = client.post(
        "/manager/employees/create/",
        {
            "employee_code": "EMP-COPY-WEEK",
            "display_name": "주간 복사 직원",
            "hire_date": "2026-01-01",
            "hourly_wage": "12000",
        },
    )
    assert create.status_code == 302
    previous = client.post(
        "/manager/attendance/manual-week/",
        {
            "employee_code": "EMP-COPY-WEEK",
            "week_start": "2026-06-29",
            "batch_id": "de1c4678-52f3-4eaa-8420-f6fd74f17fe6",
            "start_0": "08:30",
            "end_0": "16:30",
            "start_1": "09:00",
            "end_1": "17:30",
        },
    )
    assert previous.status_code == 302

    copied = client.get(
        "/manager/console/?month=2026-07&employee=EMP-COPY-WEEK"
        "&week=2026-07-06&copy_previous=1"
    )
    assert copied.status_code == 200
    html = copied.content.decode()
    assert "지난주 시간을 불러왔습니다" in html
    assert 'name="start_0" value="08:30"' in html
    assert 'name="end_0" value="16:30"' in html
    assert 'name="start_1" value="09:00"' in html
    assert 'name="end_1" value="17:30"' in html
