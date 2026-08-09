"""Approval is per-shift and goes stale when a newer correction supersedes it."""

from __future__ import annotations

import datetime as dt

import pytest
from django.contrib.auth.models import User

from apps.attendance.models import PunchKind
from apps.attendance.services import approvals, corrections
from apps.attendance.services.punches import record_punch
from apps.identity.models import Employee

pytestmark = pytest.mark.django_db


def _emp() -> Employee:
    return Employee.objects.create(
        employee_code="EMP-1", display_name="직원", hire_date=dt.date(2026, 1, 1)
    )


def _shift(emp: Employee):
    return record_punch(employee=emp, kind=PunchKind.CLOCK_IN, idempotency_key="in").shift


def _manager() -> User:
    return User.objects.create_user("mgr", password="pw-123456-strong", is_staff=True)


def test_unapproved_shift_is_pending() -> None:
    shift = _shift(_emp())
    assert approvals.approval_status(shift) == approvals.PENDING


def test_approve_makes_it_approved() -> None:
    shift = _shift(_emp())
    approvals.approve_shift(manager=_manager(), shift=shift)
    assert approvals.approval_status(shift) == approvals.APPROVED


def test_correction_after_approval_makes_it_stale() -> None:
    emp = _emp()
    shift = _shift(emp)
    mgr = _manager()
    approvals.approve_shift(manager=mgr, shift=shift)
    assert approvals.approval_status(shift) == approvals.APPROVED

    corrections.create_correction(
        manager=mgr, shift=shift,
        corrected_events=[{"kind": "CLOCK_IN", "occurred_at": "z"}], reason="보정",
    )
    # The prior approval no longer matches the current state.
    assert approvals.approval_status(shift) == approvals.STALE


def test_reapproval_after_correction_restores_approved() -> None:
    emp = _emp()
    shift = _shift(emp)
    mgr = _manager()
    corrections.create_correction(
        manager=mgr, shift=shift,
        corrected_events=[{"kind": "CLOCK_IN", "occurred_at": "z"}], reason="보정",
    )
    approvals.approve_shift(manager=mgr, shift=shift)
    assert approvals.approval_status(shift) == approvals.APPROVED
