"""Reopen preserves prior snapshots; reclose supersedes with a new version."""

from __future__ import annotations

import datetime as dt

import pytest

from apps.payroll.models.close import PayrollSnapshot, PeriodStatus
from apps.payroll.services.close import (
    close_period,
    latest_snapshot,
    prepare_period,
    reopen_period,
)

pytestmark = pytest.mark.django_db

MONTH = dt.date(2026, 7, 1)
V1 = {"lines": [{"employee": "EMP-1", "net": 1_000_000, "insurance_final": True}]}
V2 = {"lines": [{"employee": "EMP-1", "net": 1_050_000, "insurance_final": True}]}


def test_reopen_requires_reason() -> None:
    period = prepare_period(MONTH)
    close_period(period=period, payload=V1)
    with pytest.raises(ValueError):
        reopen_period(period=period, reason="  ")


def test_reopen_then_reclose_versions_and_supersedes() -> None:
    period = prepare_period(MONTH)
    snap1 = close_period(period=period, payload=V1)

    reopen_period(period=period, reason="시급 정정 반영")
    period.refresh_from_db()
    assert period.status == PeriodStatus.DRAFT
    # v1 is preserved through the reopen.
    assert PayrollSnapshot.objects.filter(period=period, version=1).exists()

    snap2 = close_period(period=period, payload=V2, reason="재마감")
    assert snap2.version == 2
    assert snap2.supersedes == snap1
    # Both versions remain queryable with their own reproducible checksums.
    assert snap1.checksum != snap2.checksum
    assert latest_snapshot(period) == snap2
    assert PayrollSnapshot.objects.filter(period=period).count() == 2
