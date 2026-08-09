"""Concurrent closes on real PostgreSQL collapse to one snapshot/version."""

from __future__ import annotations

import datetime as dt
from concurrent.futures import ThreadPoolExecutor

import pytest
from django.db import connection

from apps.payroll.models.close import PayrollSnapshot
from apps.payroll.services.close import close_period, prepare_period

pytestmark = pytest.mark.django_db(transaction=True)

MONTH = dt.date(2026, 7, 1)
PAYLOAD = {"lines": [{"employee": "EMP-1", "net": 1_000_000, "insurance_final": True}]}


def test_twenty_concurrent_closes_make_one_snapshot() -> None:
    period = prepare_period(MONTH)
    errors = []

    def do():
        try:
            close_period(period=period, payload=PAYLOAD)
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)
        finally:
            connection.close()

    with ThreadPoolExecutor(max_workers=20) as ex:
        for f in [ex.submit(do) for _ in range(20)]:
            f.result()

    assert errors == []
    assert PayrollSnapshot.objects.filter(period=period).count() == 1
    assert PayrollSnapshot.objects.get(period=period).version == 1
