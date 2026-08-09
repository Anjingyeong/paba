"""Manager-entered manual deductions (taxes, union dues, savings, etc.).

The system never computes or files taxes — these are final whole-KRW amounts the
manager enters. Only YEAR_END (연말정산) may be negative (a refund/adjustment);
every other deduction is non-negative.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.core.exceptions import ValidationError

ALLOWED_DEDUCTION_KINDS = frozenset(
    {"INCOME_TAX", "LOCAL_INCOME_TAX", "UNION", "SAVINGS", "YEAR_END", "OTHER"}
)


@dataclass(frozen=True)
class ManualDeduction:
    kind: str
    amount_krw: int
    note: str


def validate_manual_deduction(item: ManualDeduction) -> None:
    if item.kind not in ALLOWED_DEDUCTION_KINDS:
        raise ValidationError(f"Unknown deduction kind: {item.kind}")
    if not isinstance(item.amount_krw, int):
        raise ValidationError("Deduction amounts must be whole KRW integers.")
    if item.amount_krw < 0 and item.kind != "YEAR_END":
        raise ValidationError("Only YEAR_END may be negative.")
    if not item.note.strip():
        raise ValidationError("A manual deduction requires an explanation note.")
