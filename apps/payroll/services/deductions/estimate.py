"""Versioned, offline insurance-premium estimation.

Rates live in ``apps/payroll/data/insurance_rates/<version>.json`` and are loaded
from disk — never fetched at runtime. Each premium is computed with the file's
per-insurance rounding. Long-term care is a percentage of the health premium.
Industrial accident is employer-only and is not in :data:`EMPLOYEE_INSURANCES`.
"""

from __future__ import annotations

import json
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal
from functools import lru_cache
from pathlib import Path

from django.core.exceptions import ValidationError

_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "insurance_rates"

_ROUNDING = {"ROUND_DOWN": ROUND_DOWN, "ROUND_HALF_UP": ROUND_HALF_UP}


class InsuranceKind:
    NATIONAL_PENSION = "NATIONAL_PENSION"
    HEALTH = "HEALTH"
    LONG_TERM_CARE = "LONG_TERM_CARE"
    EMPLOYMENT = "EMPLOYMENT"


# The four employee-side insurances. Industrial accident is deliberately excluded.
EMPLOYEE_INSURANCES = (
    InsuranceKind.NATIONAL_PENSION,
    InsuranceKind.HEALTH,
    InsuranceKind.LONG_TERM_CARE,
    InsuranceKind.EMPLOYMENT,
)


@lru_cache(maxsize=8)
def load_rates(version: str) -> dict:
    path = _DATA_DIR / f"{version}.json"
    if not path.exists():
        raise ValidationError(f"Unknown insurance rate version: {version}")
    return json.loads(path.read_text(encoding="utf-8"))


def _round(amount: Decimal, rule: str) -> int:
    return int(amount.quantize(Decimal("1"), rounding=_ROUNDING[rule]))


def estimate_premium(insurance: str, monthly_base: int, version: str) -> int:
    """Estimated employee premium in whole KRW for one insurance and month.

    Requires a rate entry that carries a source URL (rates without provenance are
    rejected). Long-term care is derived from the health premium.
    """
    if insurance not in EMPLOYEE_INSURANCES:
        raise ValidationError(f"Not an employee-side insurance: {insurance}")
    rates = load_rates(version)
    entry = rates["insurances"][insurance]
    if not entry.get("source_url"):
        raise ValidationError(f"Rate for {insurance} has no source; refusing to use it.")

    rounding = entry["rounding"]
    if insurance == InsuranceKind.LONG_TERM_CARE:
        health = rates["insurances"][InsuranceKind.HEALTH]
        health_premium = Decimal(monthly_base) * Decimal(health["employee_rate"])
        health_premium_won = Decimal(_round(health_premium, health["rounding"]))
        ltc = health_premium_won * Decimal(entry["rate_of_health_premium"])
        return _round(ltc, rounding)

    premium = Decimal(monthly_base) * Decimal(entry["employee_rate"])
    return _round(premium, rounding)
