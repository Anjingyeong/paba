from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from django.utils.dateparse import parse_datetime

from apps.attendance.models import Shift

from .corrections import effective_events
from .time_calculation import TimeResult, calculate


@dataclass(frozen=True, slots=True)
class EffectiveShiftWindow:
    events: list[dict]
    time_result: TimeResult
    touches: bool


def _event_datetime(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        return None
    return parse_datetime(value)


def effective_shift_window(
    shift: Shift,
    *,
    start: datetime,
    end: datetime,
) -> EffectiveShiftWindow:
    """Evaluate month/window membership from the authoritative corrected state.

    Raw punches are intentionally not used to decide attribution: a manager correction
    may move a shift across a day/month boundary. Payable segments are already split at
    local midnight, so segment starts are sufficient for valid work intervals. Event
    timestamps are also checked so an invalid corrected sequence in the target window
    still blocks payroll instead of disappearing from validation.
    """
    events = effective_events(shift)
    result = calculate(events)
    touches = any(start <= segment.start < end for segment in result.segments)
    event_times = [
        (event.get("kind"), _event_datetime(event.get("occurred_at"))) for event in events
    ]
    if not touches:
        touches = any(
            when is not None and start <= when < end
            for _kind, when in event_times
        )
    if not touches and "OPEN_SHIFT" in result.blockers:
        clock_ins = [when for kind, when in event_times if kind == "CLOCK_IN" and when is not None]
        # An unclosed shift keeps overlapping every later window after its actual
        # CLOCK_IN. Shift.opened_at is metadata and may differ for imported records.
        touches = bool(clock_ins) and min(clock_ins) < end
    return EffectiveShiftWindow(events=events, time_result=result, touches=touches)