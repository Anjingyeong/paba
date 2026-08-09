"""Punch state machine: legal order, idempotency, and rejected transitions."""

from __future__ import annotations

import datetime as dt

import pytest
from django.utils import timezone

from apps.attendance.models import PunchEvent, PunchKind, Shift
from apps.attendance.services.punches import InvalidPunch, record_punch
from apps.identity.models import Employee

pytestmark = pytest.mark.django_db


def _emp(code: str = "EMP-001") -> Employee:
    return Employee.objects.create(
        employee_code=code, display_name="합성직원", hire_date=dt.date(2026, 1, 1)
    )


def _punch(emp: Employee, kind: str, key: str) -> PunchEvent:
    return record_punch(employee=emp, kind=kind, idempotency_key=key)


def test_full_legal_sequence() -> None:
    emp = _emp()
    _punch(emp, PunchKind.CLOCK_IN, "k1")
    _punch(emp, PunchKind.BREAK_START, "k2")
    _punch(emp, PunchKind.BREAK_END, "k3")
    _punch(emp, PunchKind.CLOCK_OUT, "k4")
    assert PunchEvent.objects.filter(shift__employee=emp).count() == 4
    shift = Shift.objects.get(employee=emp)
    assert shift.is_open is False


def test_idempotent_resend_returns_same_event() -> None:
    emp = _emp()
    first = _punch(emp, PunchKind.CLOCK_IN, "dup")
    second = _punch(emp, PunchKind.CLOCK_IN, "dup")
    assert first.pk == second.pk
    assert PunchEvent.objects.count() == 1


def test_server_authoritative_timestamp() -> None:
    emp = _emp()
    before = timezone.now()
    event = _punch(emp, PunchKind.CLOCK_IN, "k")
    assert before <= event.occurred_at <= timezone.now()


def test_clock_out_without_open_shift_rejected() -> None:
    emp = _emp()
    with pytest.raises(InvalidPunch) as exc:
        _punch(emp, PunchKind.CLOCK_OUT, "k")
    assert exc.value.code == "NO_OPEN_SHIFT"


def test_second_clock_in_without_clock_out_rejected() -> None:
    emp = _emp()
    _punch(emp, PunchKind.CLOCK_IN, "k1")
    with pytest.raises(InvalidPunch) as exc:
        _punch(emp, PunchKind.CLOCK_IN, "k2")
    assert exc.value.code == "SHIFT_ALREADY_OPEN"


def test_break_end_without_break_start_rejected() -> None:
    emp = _emp()
    _punch(emp, PunchKind.CLOCK_IN, "k1")
    with pytest.raises(InvalidPunch):
        _punch(emp, PunchKind.BREAK_END, "k2")


def test_double_break_start_rejected() -> None:
    emp = _emp()
    _punch(emp, PunchKind.CLOCK_IN, "k1")
    _punch(emp, PunchKind.BREAK_START, "k2")
    with pytest.raises(InvalidPunch):
        _punch(emp, PunchKind.BREAK_START, "k3")


def test_new_shift_allowed_after_clock_out() -> None:
    emp = _emp()
    _punch(emp, PunchKind.CLOCK_IN, "k1")
    _punch(emp, PunchKind.CLOCK_OUT, "k2")
    _punch(emp, PunchKind.CLOCK_IN, "k3")  # new shift
    assert Shift.objects.filter(employee=emp).count() == 2
    assert Shift.objects.filter(employee=emp, closed_at__isnull=True).count() == 1
