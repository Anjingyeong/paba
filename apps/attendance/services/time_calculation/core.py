"""Deterministic payable-time calculation with exact Decimal arithmetic.

Given a shift's effective punch events (raw or corrected), produce payable-time
segments split at:

- **midnight** boundaries (which also cover calendar-month and Mon-Sun week
  boundaries — the pay period is the Asia/Seoul calendar month),
- **rate-change** instants supplied by the caller (wage effective dates), and
- the employee's **employment** start/end (time outside employment is excluded).

Only *recorded* break intervals are unpaid. Rules that cannot be evaluated from
evidence return a **blocker** code and no segments (never a guessed number):

- ``OPEN_SHIFT`` — no CLOCK_OUT,
- ``UNPAIRED_BREAK`` — a BREAK_START without a matching BREAK_END,
- ``ILLEGAL_SEQUENCE`` — events out of the legal order,
- ``UNRECORDED_SCHEDULED_BREAK`` — terms schedule a break but none was recorded.

Durations are exact: ``Decimal(seconds) / 3600``; nothing is rounded here. The
result is independent of the order events are supplied in.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal

from django.utils.dateparse import parse_datetime

SECONDS_PER_HOUR = Decimal(3600)
_ONE_DAY = timedelta(days=1)


@dataclass(frozen=True)
class PayableSegment:
    start: datetime
    end: datetime

    @property
    def hours(self) -> Decimal:
        seconds = Decimal(str((self.end - self.start).total_seconds()))
        return seconds / SECONDS_PER_HOUR


@dataclass
class TimeResult:
    segments: list[PayableSegment] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)

    @property
    def total_hours(self) -> Decimal:
        return sum((s.hours for s in self.segments), Decimal(0))

    @property
    def ok(self) -> bool:
        return not self.blockers


def _parse(value) -> datetime:
    if isinstance(value, datetime):
        return value
    parsed = parse_datetime(value)
    if parsed is None:
        raise ValueError(f"Unparseable datetime: {value!r}")
    return parsed


def _midnights_between(start: datetime, end: datetime) -> list[datetime]:
    """All local midnights strictly inside (start, end)."""
    points: list[datetime] = []
    day = start.replace(hour=0, minute=0, second=0, microsecond=0)
    while day <= end:
        if start < day < end:
            points.append(day)
        day = (day + _ONE_DAY).replace(hour=0, minute=0, second=0, microsecond=0)
    return points


def _work_intervals(events: list[dict]) -> tuple[list[tuple[datetime, datetime]], list[str]]:
    """Reduce the punch sequence to worked (non-break) intervals, or blockers."""
    parsed = sorted(
        ({"kind": e["kind"], "at": _parse(e["occurred_at"])} for e in events),
        key=lambda e: e["at"],
    )
    blockers: list[str] = []
    kinds = [e["kind"] for e in parsed]

    if not kinds or kinds[0] != "CLOCK_IN":
        return [], ["ILLEGAL_SEQUENCE"]
    if kinds[-1] != "CLOCK_OUT":
        return [], ["OPEN_SHIFT"]

    intervals: list[tuple[datetime, datetime]] = []
    work_start = parsed[0]["at"]
    state = "WORKING"
    break_start: datetime | None = None

    for ev in parsed[1:]:
        kind, at = ev["kind"], ev["at"]
        if state == "WORKING" and kind == "BREAK_START":
            intervals.append((work_start, at))
            state, break_start = "ON_BREAK", at
        elif state == "ON_BREAK" and kind == "BREAK_END":
            state, work_start, break_start = "WORKING", at, None
        elif state == "WORKING" and kind == "CLOCK_OUT":
            intervals.append((work_start, at))
            state = "DONE"
        else:
            blockers.append("ILLEGAL_SEQUENCE")
            break

    if state == "ON_BREAK" and break_start is not None:
        blockers.append("UNPAIRED_BREAK")
    if blockers:
        return [], blockers
    # Drop zero/negative intervals defensively.
    intervals = [(s, e) for (s, e) in intervals if e > s]
    return intervals, []


def _split(
    interval: tuple[datetime, datetime], extra_points: list[datetime]
) -> list[PayableSegment]:
    start, end = interval
    cuts = set(_midnights_between(start, end))
    cuts.update(p for p in extra_points if start < p < end)
    ordered = sorted(cuts)
    segments: list[PayableSegment] = []
    cursor = start
    for point in ordered:
        segments.append(PayableSegment(cursor, point))
        cursor = point
    segments.append(PayableSegment(cursor, end))
    return segments


def calculate(
    events: list[dict],
    *,
    rate_change_points: list | None = None,
    scheduled_break_minutes: int = 0,
    employment_start=None,
    employment_end=None,
) -> TimeResult:
    intervals, blockers = _work_intervals(events)
    if blockers:
        return TimeResult(blockers=blockers)

    had_break = any(e["kind"] == "BREAK_START" for e in events)
    if scheduled_break_minutes > 0 and not had_break:
        return TimeResult(blockers=["UNRECORDED_SCHEDULED_BREAK"])

    emp_start = _parse(employment_start) if employment_start else None
    emp_end = _parse(employment_end) if employment_end else None
    rate_points = [_parse(p) for p in (rate_change_points or [])]

    segments: list[PayableSegment] = []
    for start, end in intervals:
        # Clip to the employment window (time outside employment is not payable).
        if emp_start and start < emp_start:
            start = emp_start
        if emp_end and end > emp_end:
            end = emp_end
        if end <= start:
            continue
        segments.extend(_split((start, end), rate_points))

    segments.sort(key=lambda s: s.start)
    return TimeResult(segments=segments)
