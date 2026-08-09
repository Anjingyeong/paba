"""Close is verification-gated and produces an immutable, checksummed snapshot."""

from __future__ import annotations

import datetime as dt

import pytest
from django.db import InternalError, ProgrammingError, transaction
from django.utils import timezone

from apps.attendance.models import PunchEvent, PunchKind, Shift
from apps.identity.models import Employee
from apps.payroll.models.close import PayrollSnapshot, PeriodStatus, SnapshotImmutableError
from apps.payroll.services.close import (
    CloseBlocked,
    checksum_of,
    close_period,
    prepare_period,
)

pytestmark = pytest.mark.django_db

MONTH = dt.date(2026, 7, 1)
GOOD_PAYLOAD = {"lines": [{"employee": "EMP-1", "net": 1_500_000, "insurance_final": True}]}


def _period():
    return prepare_period(MONTH)


def test_clean_close_writes_snapshot_v1() -> None:
    period = _period()
    snap = close_period(period=period, payload=GOOD_PAYLOAD)
    period.refresh_from_db()
    assert snap.version == 1
    assert period.status == PeriodStatus.CLOSED
    assert snap.checksum == checksum_of(GOOD_PAYLOAD)


def test_checksum_is_reproducible() -> None:
    assert checksum_of(GOOD_PAYLOAD) == checksum_of({"lines": [dict(GOOD_PAYLOAD["lines"][0])]})


def _open_shift_with_event_at(emp: Employee, when: dt.datetime, key: str) -> Shift:
    shift = Shift.objects.create(employee=emp)  # open (no closed_at)
    PunchEvent.objects.create(
        shift=shift, kind=PunchKind.CLOCK_IN,
        occurred_at=timezone.make_aware(when), idempotency_key=key,
    )
    return shift


def test_open_shift_in_month_blocks_close() -> None:
    period = _period()  # July
    emp = Employee.objects.create(
        employee_code="EMP-1", display_name="직원", hire_date=dt.date(2026, 1, 1)
    )
    _open_shift_with_event_at(emp, dt.datetime(2026, 7, 10, 9, 0), "jul-open")
    with pytest.raises(CloseBlocked) as exc:
        close_period(period=period, payload=GOOD_PAYLOAD)
    assert "OPEN_SHIFT" in exc.value.blockers


def test_open_shift_in_later_month_does_not_block() -> None:
    period = _period()  # July
    emp = Employee.objects.create(
        employee_code="EMP-1", display_name="직원", hire_date=dt.date(2026, 1, 1)
    )
    # Someone currently clocked in (August) must not block July's close.
    _open_shift_with_event_at(emp, dt.datetime(2026, 8, 3, 9, 0), "aug-open")
    snap = close_period(period=period, payload=GOOD_PAYLOAD)
    assert snap.version == 1


def test_negative_net_and_insurance_block_close() -> None:
    period = _period()
    payload = {"lines": [{"employee": "EMP-1", "net": -1, "insurance_final": False}]}
    with pytest.raises(CloseBlocked) as exc:
        close_period(period=period, payload=payload)
    assert "NEGATIVE_NET" in exc.value.blockers
    assert "INSURANCE_NOT_FINAL" in exc.value.blockers


def test_unapproved_shift_in_month_blocks_close() -> None:
    period = _period()
    emp = Employee.objects.create(
        employee_code="EMP-1", display_name="직원", hire_date=dt.date(2026, 1, 1)
    )
    shift = Shift.objects.create(employee=emp, closed_at=timezone.now())
    PunchEvent.objects.create(
        shift=shift, kind=PunchKind.CLOCK_IN,
        occurred_at=timezone.make_aware(dt.datetime(2026, 7, 10, 9, 0)),
        idempotency_key="july-in",
    )
    with pytest.raises(CloseBlocked) as exc:
        close_period(period=period, payload=GOOD_PAYLOAD)
    assert "UNAPPROVED_CORRECTION" in exc.value.blockers


def test_snapshot_is_immutable_at_model_and_db() -> None:
    period = _period()
    snap = close_period(period=period, payload=GOOD_PAYLOAD)

    snap.reason = "tamper"
    with pytest.raises(SnapshotImmutableError):
        snap.save()
    with pytest.raises(SnapshotImmutableError):
        snap.delete()

    with pytest.raises((InternalError, ProgrammingError)), transaction.atomic():
        PayrollSnapshot.objects.filter(pk=snap.pk).update(reason="tamper")
    with pytest.raises((InternalError, ProgrammingError)), transaction.atomic():
        PayrollSnapshot.objects.filter(pk=snap.pk).delete()
