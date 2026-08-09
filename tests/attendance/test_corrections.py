"""Corrections supersede without mutating raw punches; requests are self-only."""

from __future__ import annotations

import datetime as dt

import pytest
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from apps.attendance.models import PunchEvent, PunchKind, ShiftCorrection
from apps.attendance.services import corrections
from apps.attendance.services.punches import record_punch
from apps.auditlog.authorization import AuthorizationError
from apps.auditlog.services import digest_state
from apps.identity.models import Employee

pytestmark = pytest.mark.django_db


def _emp(code: str = "EMP-1") -> Employee:
    return Employee.objects.create(
        employee_code=code, display_name="직원", hire_date=dt.date(2026, 1, 1)
    )


def _shift_with_in(emp: Employee):
    event = record_punch(employee=emp, kind=PunchKind.CLOCK_IN, idempotency_key=f"in-{emp.pk}")
    return event.shift


def _manager() -> User:
    return User.objects.create_user("mgr", password="pw-123456-strong", is_staff=True)


def test_employee_can_request_correction_for_own_shift() -> None:
    emp = _emp()
    shift = _shift_with_in(emp)
    req = corrections.request_correction(employee=emp, shift=shift, reason="퇴근 누락")
    assert req.pk is not None


def test_employee_cannot_request_for_others_shift() -> None:
    owner = _emp("EMP-OWNER")
    other = _emp("EMP-OTHER")
    shift = _shift_with_in(owner)
    with pytest.raises(AuthorizationError):
        corrections.request_correction(employee=other, shift=shift, reason="침해 시도")


def test_reason_is_required() -> None:
    emp = _emp()
    shift = _shift_with_in(emp)
    with pytest.raises(ValidationError):
        corrections.request_correction(employee=emp, shift=shift, reason="   ")


def test_correction_does_not_mutate_raw_events() -> None:
    emp = _emp()
    shift = _shift_with_in(emp)
    raw_before = corrections.raw_event_state(shift)
    digest_before = digest_state({"events": raw_before})

    corrections.create_correction(
        manager=_manager(),
        shift=shift,
        corrected_events=[
            {"kind": "CLOCK_IN", "occurred_at": "2026-07-01T09:00:00+09:00"},
            {"kind": "CLOCK_OUT", "occurred_at": "2026-07-01T18:00:00+09:00"},
        ],
        reason="퇴근 보정",
    )

    # Raw punches are untouched; only the correction layer changed.
    assert PunchEvent.objects.filter(shift=shift).count() == 1
    assert digest_state({"events": corrections.raw_event_state(shift)}) == digest_before
    assert corrections.effective_events(shift)[-1]["kind"] == "CLOCK_OUT"


def test_correction_chain_only_grows() -> None:
    emp = _emp()
    shift = _shift_with_in(emp)
    mgr = _manager()
    c1 = corrections.create_correction(
        manager=mgr, shift=shift, corrected_events=[{"kind": "CLOCK_IN", "occurred_at": "x"}],
        reason="1차",
    )
    c2 = corrections.create_correction(
        manager=mgr, shift=shift, corrected_events=[{"kind": "CLOCK_IN", "occurred_at": "y"}],
        reason="2차",
    )
    assert c2.supersedes == c1
    assert ShiftCorrection.objects.filter(shift=shift).count() == 2
    assert corrections.current_correction(shift) == c2
