"""Payroll domain models.

Todo 3 establishes the effective-dated *policy* layer. Later todos add the
calculation, close, and export models alongside these.
"""

from __future__ import annotations

from .close import (
    PayrollPeriod,
    PayrollSnapshot,
    PeriodStatus,
    SnapshotImmutableError,
)
from .deductions import (
    InsuranceKindChoices,
    InsuranceReconciliation,
    InsuranceStatus,
)
from .policies import (
    ApplicabilityDecision,
    EmploymentTerms,
    HeadcountBracket,
    HourlyWage,
    InsuranceApplicability,
    StoreHeadcountBracket,
    WeeklyAllowanceApplicability,
    default_applicability_for,
)

__all__ = [
    "ApplicabilityDecision",
    "EmploymentTerms",
    "HeadcountBracket",
    "HourlyWage",
    "InsuranceApplicability",
    "InsuranceKindChoices",
    "InsuranceReconciliation",
    "InsuranceStatus",
    "PayrollPeriod",
    "PayrollSnapshot",
    "PeriodStatus",
    "SnapshotImmutableError",
    "StoreHeadcountBracket",
    "WeeklyAllowanceApplicability",
    "default_applicability_for",
]
