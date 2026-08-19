from __future__ import annotations

import datetime as dt

from apps.payroll.management.commands.finalize_previous_payroll import (
    pay_date_for_month,
    previous_month,
)


def test_previous_month_handles_normal_month() -> None:
    assert previous_month(dt.date(2026, 8, 19)) == dt.date(2026, 7, 1)


def test_previous_month_handles_year_boundary() -> None:
    assert previous_month(dt.date(2026, 1, 3)) == dt.date(2025, 12, 1)


def test_pay_date_uses_following_month() -> None:
    assert pay_date_for_month(dt.date(2026, 7, 1), 5) == dt.date(2026, 8, 5)


def test_pay_date_handles_december() -> None:
    assert pay_date_for_month(dt.date(2026, 12, 1), 28) == dt.date(2027, 1, 28)