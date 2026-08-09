"""Deductions: versioned insurance estimates, institution reconciliation, and
manager-entered manual deductions (taxes etc.).

Insurance premiums are *estimated* from a pinned, versioned rate file with no
runtime network calls; the manager then reconciles each against the institution's
notice. Industrial-accident insurance is employer-only and never an employee
deduction. Taxes and other deductions are manager-entered final amounts — the
system never computes or files taxes.
"""

from __future__ import annotations

from .estimate import (
    EMPLOYEE_INSURANCES,
    InsuranceKind,
    estimate_premium,
    load_rates,
)
from .manual import ALLOWED_DEDUCTION_KINDS, ManualDeduction, validate_manual_deduction

__all__ = [
    "ALLOWED_DEDUCTION_KINDS",
    "EMPLOYEE_INSURANCES",
    "InsuranceKind",
    "ManualDeduction",
    "estimate_premium",
    "load_rates",
    "validate_manual_deduction",
]
