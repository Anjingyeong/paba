"""Manual deductions are validated manager finals; no tax is computed."""

from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError

from apps.payroll.services.deductions import ManualDeduction, validate_manual_deduction


def test_positive_income_tax_ok() -> None:
    validate_manual_deduction(ManualDeduction("INCOME_TAX", 33_000, "간이세액표"))


def test_unknown_kind_rejected() -> None:
    with pytest.raises(ValidationError):
        validate_manual_deduction(ManualDeduction("MYSTERY", 1000, "x"))


def test_negative_only_allowed_for_year_end() -> None:
    validate_manual_deduction(ManualDeduction("YEAR_END", -50_000, "연말정산 환급"))
    with pytest.raises(ValidationError):
        validate_manual_deduction(ManualDeduction("INCOME_TAX", -1, "invalid"))


def test_note_required() -> None:
    with pytest.raises(ValidationError):
        validate_manual_deduction(ManualDeduction("OTHER", 1000, "   "))


def test_non_integer_amount_rejected() -> None:
    with pytest.raises(ValidationError):
        validate_manual_deduction(ManualDeduction("OTHER", 1000.5, "decimal"))  # type: ignore[arg-type]
