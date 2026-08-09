"""Golden tests for payable-time calculation: exact Decimal, boundary splitting."""

from __future__ import annotations

import random
from decimal import Decimal

from apps.attendance.services.time_calculation import calculate


def _ev(kind: str, at: str) -> dict:
    return {"kind": kind, "occurred_at": at}


def test_thirty_second_fraction_is_exact() -> None:
    result = calculate([
        _ev("CLOCK_IN", "2026-07-01T09:00:00+09:00"),
        _ev("CLOCK_OUT", "2026-07-01T09:00:30+09:00"),
    ])
    assert result.ok
    assert result.total_hours == Decimal("30") / Decimal("3600")


def test_recorded_break_is_unpaid() -> None:
    result = calculate([
        _ev("CLOCK_IN", "2026-07-01T09:00:00+09:00"),
        _ev("BREAK_START", "2026-07-01T12:00:00+09:00"),
        _ev("BREAK_END", "2026-07-01T13:00:00+09:00"),
        _ev("CLOCK_OUT", "2026-07-01T18:00:00+09:00"),
    ])
    assert result.ok
    assert result.total_hours == Decimal(8)  # 9 hours span - 1 hour break


def test_overnight_splits_at_midnight() -> None:
    result = calculate([
        _ev("CLOCK_IN", "2026-07-01T23:30:00+09:00"),
        _ev("CLOCK_OUT", "2026-07-02T00:30:00+09:00"),
    ])
    assert result.ok
    assert len(result.segments) == 2
    assert result.total_hours == Decimal(1)
    assert result.segments[0].end.isoformat() == "2026-07-02T00:00:00+09:00"


def test_month_and_week_boundary_split() -> None:
    # 2026-07-31 (Fri) 23:00 -> 2026-08-01 (Sat) 01:00 crosses the month boundary.
    result = calculate([
        _ev("CLOCK_IN", "2026-07-31T23:00:00+09:00"),
        _ev("CLOCK_OUT", "2026-08-01T01:00:00+09:00"),
    ])
    assert result.ok
    assert len(result.segments) == 2
    assert result.total_hours == Decimal(2)
    assert result.segments[0].end.month == 8
    assert result.segments[0].end.day == 1


def test_mid_shift_rate_change_split() -> None:
    result = calculate(
        [
            _ev("CLOCK_IN", "2026-07-01T09:00:00+09:00"),
            _ev("CLOCK_OUT", "2026-07-01T17:00:00+09:00"),
        ],
        rate_change_points=["2026-07-01T13:00:00+09:00"],
    )
    assert result.ok
    assert len(result.segments) == 2
    assert result.segments[0].hours == Decimal(4)
    assert result.segments[1].hours == Decimal(4)


def test_employment_window_clips_time() -> None:
    # Employee joins at 10:00; the 09:00-11:00 shift only counts from 10:00.
    result = calculate(
        [
            _ev("CLOCK_IN", "2026-07-01T09:00:00+09:00"),
            _ev("CLOCK_OUT", "2026-07-01T11:00:00+09:00"),
        ],
        employment_start="2026-07-01T10:00:00+09:00",
    )
    assert result.ok
    assert result.total_hours == Decimal(1)


def test_open_shift_is_blocked() -> None:
    result = calculate([_ev("CLOCK_IN", "2026-07-01T09:00:00+09:00")])
    assert not result.ok
    assert result.blockers == ["OPEN_SHIFT"]


def test_unpaired_break_is_blocked() -> None:
    result = calculate([
        _ev("CLOCK_IN", "2026-07-01T09:00:00+09:00"),
        _ev("BREAK_START", "2026-07-01T12:00:00+09:00"),
        _ev("CLOCK_OUT", "2026-07-01T18:00:00+09:00"),
    ])
    assert not result.ok
    assert "ILLEGAL_SEQUENCE" in result.blockers or "UNPAIRED_BREAK" in result.blockers


def test_unrecorded_scheduled_break_is_blocked() -> None:
    result = calculate(
        [
            _ev("CLOCK_IN", "2026-07-01T09:00:00+09:00"),
            _ev("CLOCK_OUT", "2026-07-01T18:00:00+09:00"),
        ],
        scheduled_break_minutes=60,
    )
    assert not result.ok
    assert result.blockers == ["UNRECORDED_SCHEDULED_BREAK"]


def test_result_is_independent_of_input_order() -> None:
    events = [
        _ev("CLOCK_IN", "2026-07-01T09:00:00+09:00"),
        _ev("BREAK_START", "2026-07-01T12:00:00+09:00"),
        _ev("BREAK_END", "2026-07-01T12:30:00+09:00"),
        _ev("CLOCK_OUT", "2026-07-01T18:00:00+09:00"),
    ]
    baseline = calculate(events).total_hours
    for _ in range(5):
        shuffled = events[:]
        random.shuffle(shuffled)
        assert calculate(shuffled).total_hours == baseline
    assert baseline == Decimal("8.5")
