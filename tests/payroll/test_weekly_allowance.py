"""Weekly allowance: candidate thresholds, manager confirmation, hour formulas."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from apps.payroll.services.earnings import (
    WeeklyAllowanceDecision,
    WeeklyAllowanceFacts,
    is_candidate,
    weekly_allowance_amount,
    weekly_allowance_hours,
)
from apps.payroll.services.earnings.weekly_allowance import APPLICABLE, NOT_APPLICABLE


def _facts(**kw) -> WeeklyAllowanceFacts:
    base = {
        "avg_weekly_scheduled_hours": Decimal("40"),
        "full_attendance": True,
        "employed": True,
        "is_short_time": False,
        "daily_scheduled_hours": Decimal("8"),
        "four_week_scheduled_hours": Decimal("160"),
        "ordinary_reference_days": Decimal("20"),
        "ordinary_hourly_wage": 12000,
    }
    base.update(kw)
    return WeeklyAllowanceFacts(**base)


def test_candidate_threshold_15_hours() -> None:
    assert is_candidate(_facts(avg_weekly_scheduled_hours=Decimal("15.00"))) is True
    assert is_candidate(_facts(avg_weekly_scheduled_hours=Decimal("14.99"))) is False


def test_absence_or_no_employment_is_not_candidate() -> None:
    assert is_candidate(_facts(full_attendance=False)) is False
    assert is_candidate(_facts(employed=False)) is False


def test_regular_worker_hours_is_daily_scheduled() -> None:
    assert weekly_allowance_hours(_facts(daily_scheduled_hours=Decimal("8"))) == Decimal("8")


def test_short_time_worker_hours_formula() -> None:
    # 48 scheduled hours over 4 weeks ÷ 24 ordinary reference days = 2 hours.
    facts = _facts(
        is_short_time=True,
        four_week_scheduled_hours=Decimal("48"),
        ordinary_reference_days=Decimal("24"),
    )
    assert weekly_allowance_hours(facts) == Decimal("2")


def test_amount_requires_applicable_decision() -> None:
    facts = _facts()
    applicable = WeeklyAllowanceDecision(APPLICABLE, "주15시간 이상, 개근")
    not_applicable = WeeklyAllowanceDecision(NOT_APPLICABLE, "단기 근로 종료")
    assert weekly_allowance_amount(facts, applicable) == 96_000  # 8h × 12,000
    assert weekly_allowance_amount(facts, not_applicable) == 0


def test_decision_requires_reason() -> None:
    with pytest.raises(ValueError):
        weekly_allowance_amount(_facts(), WeeklyAllowanceDecision(APPLICABLE, "  "))


def test_no_twenty_percent_shortcut_in_source() -> None:
    pkg = Path("apps/payroll/services/earnings")
    for path in pkg.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "0.2" not in text
        assert "base *" not in text and "base*" not in text
