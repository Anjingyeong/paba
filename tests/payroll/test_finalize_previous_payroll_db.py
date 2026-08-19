from __future__ import annotations

import datetime as dt
from io import StringIO

import pytest
from django.contrib.auth.models import User
from django.core.management import call_command
from django.db.backends.postgresql.psycopg_any import DateRange
from django.utils import timezone

from apps.attendance.models import PunchEvent, PunchKind, Shift
from apps.attendance.services.approvals import approve_shift
from apps.core.models import Store
from apps.identity.models import Employee
from apps.payroll.models import HourlyWage, PayrollPeriod, PeriodStatus
from apps.payroll.services.close import latest_snapshot

pytestmark = pytest.mark.django_db


def test_auto_finalize_closes_ready_previous_month(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "apps.payroll.management.commands.finalize_previous_payroll.timezone.localdate",
        lambda: dt.date(2026, 8, 19),
    )
    store = Store.get()
    store.payroll_pay_day = 5
    store.auto_payroll_close_enabled = True
    store.save(update_fields=["payroll_pay_day", "auto_payroll_close_enabled", "updated_at"])

    employee = Employee.objects.create(
        employee_code="EMP-AUTO-1",
        display_name="자동 마감 직원",
        hire_date=dt.date(2026, 1, 1),
    )
    HourlyWage.objects.create(
        employee=employee,
        hourly_wage=12_000,
        effective=DateRange(dt.date(2026, 1, 1), None),
    )
    start = timezone.make_aware(dt.datetime(2026, 7, 10, 9, 0))
    end = timezone.make_aware(dt.datetime(2026, 7, 10, 17, 0))
    shift = Shift.objects.create(employee=employee, closed_at=end)
    PunchEvent.objects.create(
        shift=shift,
        kind=PunchKind.CLOCK_IN,
        occurred_at=start,
        idempotency_key="auto-in",
    )
    PunchEvent.objects.create(
        shift=shift,
        kind=PunchKind.CLOCK_OUT,
        occurred_at=end,
        idempotency_key="auto-out",
    )
    manager = User.objects.create_user("auto-close-manager", is_staff=True)
    approve_shift(manager=manager, shift=shift)

    stdout = StringIO()
    call_command("finalize_previous_payroll", stdout=stdout, stderr=StringIO())

    period = PayrollPeriod.objects.get(month=dt.date(2026, 7, 1))
    assert period.status == PeriodStatus.CLOSED
    snapshot = latest_snapshot(period)
    assert snapshot is not None
    assert snapshot.payload["pay_date"] == "2026-08-05"
    assert snapshot.payload["lines"][0]["gross"] == 96_000
    assert "statements are ready" in stdout.getvalue()