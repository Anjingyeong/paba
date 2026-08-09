"""KRW rounding is ROUND_CEILING, applied once at the end of positive earnings."""

from __future__ import annotations

from decimal import Decimal

from apps.core.money import ceil_won
from apps.payroll.services.earnings import RatedSegment, calculate_base_pay


def test_half_won_rounds_up() -> None:
    # 1 second at 1,800/h = 0.5 KRW -> 1.
    result = calculate_base_pay([RatedSegment(Decimal(1) / Decimal(3600), 1800)])
    assert result.gross_decimal == Decimal("0.5")
    assert result.amount_krw == 1


def test_exact_integer_not_bumped() -> None:
    assert ceil_won(Decimal("100")) == 100


def test_tiny_fraction_rounds_up() -> None:
    assert ceil_won(Decimal("100.01")) == 101


def test_ceiling_never_rounds_down() -> None:
    assert ceil_won(Decimal("100.99")) == 101
    assert ceil_won(Decimal("0.0001")) == 1
