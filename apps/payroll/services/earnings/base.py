"""Base pay = Σ (payable hours × point-in-time hourly wage).

Hours come pre-split by the time engine so each :class:`RatedSegment` maps to a
single wage. Amounts accumulate as exact ``Decimal`` and are rounded up to whole
won exactly once, at the end. Base pay is always positive; negative adjustments are
a separate manager-entered item (see :mod:`.manual`) and are never ceiling-rounded.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from apps.core.money import ceil_won


@dataclass(frozen=True)
class RatedSegment:
    hours: Decimal
    hourly_wage: int  # whole KRW per hour, in force for this segment


@dataclass(frozen=True)
class BasePayResult:
    amount_krw: int
    gross_decimal: Decimal
    explanation: list[dict] = field(default_factory=list)


def calculate_base_pay(segments: list[RatedSegment]) -> BasePayResult:
    total = Decimal(0)
    explanation: list[dict] = []
    for seg in segments:
        if seg.hours < 0:
            raise ValueError("Payable hours cannot be negative.")
        subtotal = seg.hours * seg.hourly_wage
        total += subtotal
        explanation.append(
            {"hours": str(seg.hours), "hourly_wage": seg.hourly_wage, "subtotal": str(subtotal)}
        )
    return BasePayResult(amount_krw=ceil_won(total), gross_decimal=total, explanation=explanation)
