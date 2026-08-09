"""Concurrency: idempotent double-taps and clock-out races on real PostgreSQL."""

from __future__ import annotations

import datetime as dt
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from django.db import connection

from apps.attendance.models import PunchEvent, PunchKind, Shift
from apps.attendance.services.punches import InvalidPunch, record_punch
from apps.identity.models import Employee

# transaction=True gives each thread a real, committing connection.
pytestmark = pytest.mark.django_db(transaction=True)


def _emp(code: str = "EMP-CC") -> Employee:
    return Employee.objects.create(
        employee_code=code, display_name="합성직원", hire_date=dt.date(2026, 1, 1)
    )


def _run(fn, n: int):
    results, errors = [], []

    def worker():
        try:
            results.append(fn())
        except Exception as exc:  # noqa: BLE001 - collecting for assertions
            errors.append(exc)
        finally:
            connection.close()

    with ThreadPoolExecutor(max_workers=n) as ex:
        for f in [ex.submit(worker) for _ in range(n)]:
            f.result()
    return results, errors


def test_20_identical_clock_ins_make_one_event() -> None:
    emp = _emp()
    results, errors = _run(
        lambda: record_punch(employee=emp, kind=PunchKind.CLOCK_IN, idempotency_key="same"),
        20,
    )
    assert errors == []
    assert PunchEvent.objects.filter(kind=PunchKind.CLOCK_IN).count() == 1
    assert Shift.objects.filter(employee=emp, closed_at__isnull=True).count() == 1
    # Every caller observed the one canonical event.
    assert len({r.pk for r in results}) == 1


def test_concurrent_distinct_clock_outs_close_once() -> None:
    emp = _emp()
    record_punch(employee=emp, kind=PunchKind.CLOCK_IN, idempotency_key="in")

    def clock_out():
        return record_punch(
            employee=emp, kind=PunchKind.CLOCK_OUT, idempotency_key=f"out-{uuid.uuid4().hex}"
        )

    results, errors = _run(clock_out, 5)
    assert PunchEvent.objects.filter(kind=PunchKind.CLOCK_OUT).count() == 1
    assert Shift.objects.filter(employee=emp, closed_at__isnull=True).count() == 0
    # Exactly one succeeded; the rest saw no open shift.
    assert len(results) == 1
    assert all(isinstance(e, InvalidPunch) for e in errors)
