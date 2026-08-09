"""Manager-entered earnings items.

Bonus / overtime / night / holiday / other pay and negative adjustments are never
calculated by the system — the manager enters a final whole-KRW amount plus an
explanation (hours and/or formula note). Only ``ADJUSTMENT`` may be negative, and
negative amounts are never ceiling-rounded.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.core.exceptions import ValidationError

ALLOWED_MANUAL_KINDS = frozenset(
    {"BONUS", "OVERTIME", "NIGHT", "HOLIDAY", "OTHER", "ADJUSTMENT"}
)


@dataclass(frozen=True)
class ManualEarning:
    kind: str
    amount_krw: int  # whole KRW; only ADJUSTMENT may be negative
    note: str  # hours and/or formula explanation entered by the manager


def validate_manual_earning(item: ManualEarning) -> None:
    if item.kind not in ALLOWED_MANUAL_KINDS:
        raise ValidationError(f"Unknown manual earning kind: {item.kind}")
    if not isinstance(item.amount_krw, int):
        raise ValidationError("Manual amounts must be whole KRW integers.")
    if item.amount_krw < 0 and item.kind != "ADJUSTMENT":
        raise ValidationError("Only ADJUSTMENT items may be negative.")
    if not item.note.strip():
        raise ValidationError("A manual earning requires an explanation note.")
