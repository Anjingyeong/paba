from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest

from apps.payroll.services.month_close import PayrollBuildBlocked, build_month_payload
from apps.payroll.services.preview import MonthlyPayrollLine

MONTH = dt.date(2026, 8, 1)
PAY_DATE = dt.date(2026, 9, 5)


def test_build_month_payload_freezes_hourly_preview(monkeypatch: pytest.MonkeyPatch) -> None:
    line = MonthlyPayrollLine(
        employee_code="EMP-001",
        display_name="직원",
        total_hours=Decimal("80.50"),
        hourly_wage=12_000,
        gross_pay=966_000,
        blockers=(),
    )
    monkeypatch.setattr(
        "apps.payroll.services.month_close.monthly_payroll_lines",
        lambda month: [line],
    )

    payload = build_month_payload(MONTH, pay_date=PAY_DATE)

    assert payload["pay_date"] == "2026-09-05"
    assert payload["calc_period"] == "2026-08"
    assert payload["lines"][0]["employee_id"] == "EMP-001"
    assert payload["lines"][0]["gross"] == 966_000
    assert payload["lines"][0]["net"] == 966_000
    assert payload["lines"][0]["earnings"] == [{"label": "기본급", "amount": 966_000}]
    assert payload["lines"][0]["deductions"] == []


def test_build_month_payload_blocks_incomplete_preview(monkeypatch: pytest.MonkeyPatch) -> None:
    line = MonthlyPayrollLine(
        employee_code="EMP-001",
        display_name="직원",
        total_hours=Decimal("8"),
        hourly_wage=None,
        gross_pay=0,
        blockers=("MISSING_HOURLY_WAGE",),
    )
    monkeypatch.setattr(
        "apps.payroll.services.month_close.monthly_payroll_lines",
        lambda month: [line],
    )

    with pytest.raises(PayrollBuildBlocked) as exc:
        build_month_payload(MONTH, pay_date=PAY_DATE)

    assert exc.value.blockers == ["MISSING_HOURLY_WAGE"]


def test_build_month_payload_blocks_empty_month(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "apps.payroll.services.month_close.monthly_payroll_lines",
        lambda month: [],
    )

    with pytest.raises(PayrollBuildBlocked) as exc:
        build_month_payload(MONTH, pay_date=PAY_DATE)

    assert exc.value.blockers == ["NO_PAYROLL_LINES"]