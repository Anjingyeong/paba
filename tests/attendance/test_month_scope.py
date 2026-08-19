from __future__ import annotations

from datetime import datetime
from typing import cast

import pytest

from apps.attendance.models import Shift
from apps.attendance.services.month_scope import effective_shift_window

START = datetime.fromisoformat("2026-08-01T00:00:00+09:00")
END = datetime.fromisoformat("2026-09-01T00:00:00+09:00")


def test_open_shift_started_before_month_still_touches(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "apps.attendance.services.month_scope.effective_events",
        lambda shift: [{"kind": "CLOCK_IN", "occurred_at": "2026-07-31T23:00:00+09:00"}],
    )

    scoped = effective_shift_window(cast(Shift, object()), start=START, end=END)

    assert scoped.touches is True
    assert "OPEN_SHIFT" in scoped.time_result.blockers


def test_open_shift_starting_after_month_does_not_touch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "apps.attendance.services.month_scope.effective_events",
        lambda shift: [{"kind": "CLOCK_IN", "occurred_at": "2026-09-03T09:00:00+09:00"}],
    )

    scoped = effective_shift_window(cast(Shift, object()), start=START, end=END)

    assert scoped.touches is False


def test_corrected_event_sequence_is_attributed_by_effective_time(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "apps.attendance.services.month_scope.effective_events",
        lambda shift: [
            {"kind": "CLOCK_IN", "occurred_at": "2026-08-31T22:00:00+09:00"},
            {"kind": "CLOCK_OUT", "occurred_at": "2026-09-01T02:00:00+09:00"},
        ],
    )

    august = effective_shift_window(cast(Shift, object()), start=START, end=END)
    september = effective_shift_window(
        cast(Shift, object()),
        start=END,
        end=datetime.fromisoformat("2026-10-01T00:00:00+09:00"),
    )

    assert august.touches is True
    assert september.touches is True
    assert sum(segment.hours for segment in august.time_result.segments) == 4