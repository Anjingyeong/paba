"""prepare_payroll_periods is idempotent and concurrency-safe."""

from __future__ import annotations

import datetime as dt
from concurrent.futures import ThreadPoolExecutor

import pytest
from django.db import connection

from apps.payroll.models.close import PayrollPeriod, PeriodStatus
from apps.payroll.services.close import prepare_period, prepare_previous_month


@pytest.mark.django_db
def test_prepare_is_idempotent() -> None:
    prepare_period(dt.date(2026, 7, 1))
    prepare_period(dt.date(2026, 7, 15))  # same month, different day
    assert PayrollPeriod.objects.filter(month=dt.date(2026, 7, 1)).count() == 1


@pytest.mark.django_db
def test_prepare_previous_month() -> None:
    period = prepare_previous_month(dt.date(2026, 8, 9))
    assert period.month == dt.date(2026, 7, 1)
    assert period.status == PeriodStatus.DRAFT


@pytest.mark.django_db
def test_prepare_previous_month_january_wraps_year() -> None:
    period = prepare_previous_month(dt.date(2026, 1, 15))
    assert period.month == dt.date(2025, 12, 1)


@pytest.mark.django_db(transaction=True)
def test_concurrent_prepare_makes_one_period() -> None:
    def do():
        try:
            prepare_period(dt.date(2026, 7, 1))
        finally:
            connection.close()

    with ThreadPoolExecutor(max_workers=10) as ex:
        for f in [ex.submit(do) for _ in range(10)]:
            f.result()
    assert PayrollPeriod.objects.filter(month=dt.date(2026, 7, 1)).count() == 1
