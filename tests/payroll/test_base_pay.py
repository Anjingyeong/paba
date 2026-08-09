"""Base pay: exact Decimal accumulation, single end-rounding, positive-only."""

from __future__ import annotations

from decimal import Decimal

import pytest

from apps.payroll.services.earnings import RatedSegment, calculate_base_pay


def test_simple_month() -> None:
    result = calculate_base_pay([RatedSegment(Decimal("160"), 12000)])
    assert result.amount_krw == 1_920_000


def test_fractional_minute_segment() -> None:
    # 30 seconds at 12,000/h = exactly 100 KRW.
    result = calculate_base_pay([RatedSegment(Decimal(30) / Decimal(3600), 12000)])
    assert result.amount_krw == 100


def test_multiple_rate_segments_sum() -> None:
    result = calculate_base_pay(
        [RatedSegment(Decimal(4), 10000), RatedSegment(Decimal(4), 11000)]
    )
    assert result.amount_krw == 84_000


def test_no_intermediate_rounding() -> None:
    # Two 0.3-won subtotals sum to 0.6 -> ceil once = 1. Per-segment ceiling would
    # wrongly give 2.
    seg = RatedSegment(Decimal(1) / Decimal(3600), 1080)  # 0.3 KRW each
    result = calculate_base_pay([seg, seg])
    assert result.gross_decimal == Decimal("0.6")
    assert result.amount_krw == 1


def test_negative_hours_rejected() -> None:
    with pytest.raises(ValueError):
        calculate_base_pay([RatedSegment(Decimal("-1"), 10000)])
