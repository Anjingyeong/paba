"""Versioned insurance estimation: component-exact, offline, provenance-required."""

from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError

from apps.payroll.services.deductions import (
    EMPLOYEE_INSURANCES,
    InsuranceKind,
    estimate_premium,
    load_rates,
)
from apps.payroll.services.deductions import estimate as estimate_mod

VERSION = "2026.1"
BASE = 3_000_000


def test_national_pension_estimate() -> None:
    assert estimate_premium(InsuranceKind.NATIONAL_PENSION, BASE, VERSION) == 135_000


def test_health_estimate() -> None:
    assert estimate_premium(InsuranceKind.HEALTH, BASE, VERSION) == 106_350


def test_long_term_care_is_percent_of_health() -> None:
    # health premium 106,350 × 0.1295 = 13,772.325 -> floor 13,772
    assert estimate_premium(InsuranceKind.LONG_TERM_CARE, BASE, VERSION) == 13_772


def test_employment_estimate() -> None:
    assert estimate_premium(InsuranceKind.EMPLOYMENT, BASE, VERSION) == 27_000


def test_round_down_floors_fractions() -> None:
    # 1,234,567 × 0.045 = 55,555.515 -> 55,555
    assert estimate_premium(InsuranceKind.NATIONAL_PENSION, 1_234_567, VERSION) == 55_555


def test_industrial_accident_is_not_an_employee_insurance() -> None:
    assert "INDUSTRIAL_ACCIDENT" not in EMPLOYEE_INSURANCES
    with pytest.raises(ValidationError):
        estimate_premium("INDUSTRIAL_ACCIDENT", BASE, VERSION)
    rates = load_rates(VERSION)
    assert rates["industrial_accident"]["employer_only"] is True
    assert rates["industrial_accident"]["employee_rate"] == "0"


def test_unknown_version_rejected() -> None:
    with pytest.raises(ValidationError):
        estimate_premium(InsuranceKind.HEALTH, BASE, "1999.0")


def test_rate_without_source_is_refused(monkeypatch) -> None:
    def fake_load(_version: str) -> dict:
        return {"insurances": {"HEALTH": {"employee_rate": "0.03545", "rounding": "ROUND_DOWN"}}}

    monkeypatch.setattr(estimate_mod, "load_rates", fake_load)
    with pytest.raises(ValidationError):
        estimate_premium(InsuranceKind.HEALTH, BASE, VERSION)
