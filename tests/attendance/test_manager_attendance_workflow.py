from __future__ import annotations

import datetime as dt

import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.utils import timezone

from apps.attendance.models import PunchEvent, PunchKind, Shift
from apps.attendance.services import approvals, corrections
from apps.attendance.services.time_calculation import calculate
from apps.identity.auth.middleware import stamp_login
from apps.identity.models import Employee

pytestmark = pytest.mark.django_db


def _manager_client() -> Client:
    manager = User.objects.create_user("attendance-manager", is_staff=True)
    client = Client()
    client.force_login(manager)
    session = client.session
    stamp_login(session)
    session.save()
    return client


def _closed_shift() -> Shift:
    employee = Employee.objects.create(
        employee_code="EMP-ATT-1",
        display_name="근태 직원",
        hire_date=dt.date(2026, 1, 1),
    )
    start = timezone.make_aware(dt.datetime(2026, 7, 10, 9, 0))
    end = timezone.make_aware(dt.datetime(2026, 7, 10, 17, 0))
    shift = Shift.objects.create(employee=employee, closed_at=end)
    PunchEvent.objects.create(
        shift=shift,
        kind=PunchKind.CLOCK_IN,
        occurred_at=start,
        idempotency_key="manager-att-in",
    )
    PunchEvent.objects.create(
        shift=shift,
        kind=PunchKind.CLOCK_OUT,
        occurred_at=end,
        idempotency_key="manager-att-out",
    )
    return shift


def test_manager_approves_closed_shift() -> None:
    shift = _closed_shift()

    response = _manager_client().post(f"/manager/attendance/{shift.pk}/approve/")

    assert response.status_code == 302
    assert approvals.approval_status(shift) == approvals.APPROVED


def test_manager_corrects_times_and_new_state_is_approved() -> None:
    shift = _closed_shift()

    response = _manager_client().post(
        f"/manager/attendance/{shift.pk}/correct-times/",
        {
            "started_at": "2026-07-10T10:00",
            "ended_at": "2026-07-10T18:00",
            "reason": "종이 출근부 확인",
        },
    )

    assert response.status_code == 302
    corrected = corrections.current_correction(shift)
    assert corrected is not None
    assert approvals.approval_status(shift) == approvals.APPROVED
    result = calculate(corrections.effective_events(shift))
    assert result.ok
    assert result.total_hours == 8


def test_manager_records_week_and_entries_are_auto_approved() -> None:
    employee = Employee.objects.create(
        employee_code="EMP-WEEK-1",
        display_name="주간 입력 직원",
        hire_date=dt.date(2026, 1, 1),
    )

    response = _manager_client().post(
        "/manager/attendance/manual-week/",
        {
            "employee_code": employee.employee_code,
            "week_start": "2026-07-06",
            "batch_id": "4e014706-f709-4bf4-8174-a8fb2e957477",
            "start_0": "09:00",
            "end_0": "17:00",
            "start_1": "10:00",
            "end_1": "18:30",
        },
    )

    assert response.status_code == 302
    shifts = list(Shift.objects.filter(employee=employee).order_by("opened_at"))
    assert len(shifts) == 2
    assert all(approvals.approval_status(shift) == approvals.APPROVED for shift in shifts)
    assert calculate(corrections.effective_events(shifts[0])).total_hours == 8
    assert calculate(corrections.effective_events(shifts[1])).total_hours == dt.timedelta(
        hours=8, minutes=30
    ).total_seconds() / 3600


def test_manual_week_rolls_back_all_rows_when_one_overlaps() -> None:
    employee = Employee.objects.create(
        employee_code="EMP-WEEK-2",
        display_name="주간 충돌 직원",
        hire_date=dt.date(2026, 1, 1),
    )
    existing_start = timezone.make_aware(dt.datetime(2026, 7, 7, 12, 0))
    existing_end = timezone.make_aware(dt.datetime(2026, 7, 7, 16, 0))
    existing = Shift.objects.create(employee=employee, closed_at=existing_end)
    Shift.objects.filter(pk=existing.pk).update(opened_at=existing_start)
    PunchEvent.objects.create(
        shift=existing,
        kind=PunchKind.CLOCK_IN,
        occurred_at=existing_start,
        idempotency_key="existing-week-in",
    )
    PunchEvent.objects.create(
        shift=existing,
        kind=PunchKind.CLOCK_OUT,
        occurred_at=existing_end,
        idempotency_key="existing-week-out",
    )

    response = _manager_client().post(
        "/manager/attendance/manual-week/",
        {
            "employee_code": employee.employee_code,
            "week_start": "2026-07-06",
            "batch_id": "2aa0bfbe-0568-4fa7-9ef9-b34bd6556bd4",
            "start_0": "09:00",
            "end_0": "17:00",
            "start_1": "13:00",
            "end_1": "18:00",
        },
    )

    assert response.status_code == 409
    assert Shift.objects.filter(employee=employee).count() == 1