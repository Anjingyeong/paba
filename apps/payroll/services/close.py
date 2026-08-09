"""Monthly close: verification-gated, immutable, versioned snapshots.

``close_period`` refuses to close while any blocker remains, then copies the
resolved payroll into a new immutable :class:`PayrollSnapshot` inside a single
locked transaction — so concurrent closes produce exactly one snapshot. Reopen
returns the period to DRAFT without touching prior snapshots; a subsequent reclose
writes a new version that ``supersedes`` the previous one, and every version's
checksum stays reproducible.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, time

from django.db import transaction
from django.utils import timezone

from apps.attendance.models import PunchEvent, Shift
from apps.attendance.services.approvals import APPROVED, approval_status
from apps.auditlog import services as audit
from apps.payroll.models.close import PayrollPeriod, PayrollSnapshot, PeriodStatus


class CloseBlocked(Exception):
    def __init__(self, blockers: list[str]):
        super().__init__(", ".join(blockers))
        self.blockers = blockers


def _first_of_next_month(month: date) -> date:
    return date(month.year + 1, 1, 1) if month.month == 12 else date(month.year, month.month + 1, 1)


def checksum_of(payload) -> str:
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def prepare_period(month: date) -> PayrollPeriod:
    """Idempotently ensure a DRAFT period exists for the given month (1st)."""
    first = month.replace(day=1)
    period, _ = PayrollPeriod.objects.get_or_create(
        month=first, defaults={"status": PeriodStatus.DRAFT}
    )
    return period


def prepare_previous_month(today: date) -> PayrollPeriod:
    first_this = today.replace(day=1)
    prev = date(first_this.year - 1, 12, 1) if first_this.month == 1 else date(
        first_this.year, first_this.month - 1, 1
    )
    return prepare_period(prev)


def collect_blockers(period: PayrollPeriod, payload: dict) -> list[str]:
    """Return every reason the period cannot close (empty list ⇒ ready)."""
    blockers: set[str] = set()
    month = period.month
    # Timezone-aware month bounds so DateTimeField comparisons are exact.
    month_start = timezone.make_aware(datetime.combine(month, time.min))
    month_end = timezone.make_aware(datetime.combine(_first_of_next_month(month), time.min))

    # An attendance shift still open *within this month* blocks the close. A shift
    # open in a later month (e.g. someone currently clocked in) is irrelevant to a
    # prior month's close.
    open_in_month = Shift.objects.filter(
        closed_at__isnull=True,
        events__occurred_at__gte=month_start,
        events__occurred_at__lt=month_end,
    ).exists()
    if open_in_month:
        blockers.add("OPEN_SHIFT")

    # Every shift touching the month must be approved at its current state.
    shift_ids = (
        PunchEvent.objects.filter(occurred_at__gte=month_start, occurred_at__lt=month_end)
        .values_list("shift_id", flat=True)
        .distinct()
    )
    for shift in Shift.objects.filter(pk__in=list(shift_ids)):
        if approval_status(shift) != APPROVED:
            blockers.add("UNAPPROVED_CORRECTION")
            break

    # Payload-driven checks computed by the preview.
    for line in payload.get("lines", []):
        if line.get("net", 0) < 0:
            blockers.add("NEGATIVE_NET")
        if not line.get("weekly_allowance_resolved", True):
            blockers.add("WEEKLY_ALLOWANCE_UNRESOLVED")
        if not line.get("insurance_final", True):
            blockers.add("INSURANCE_NOT_FINAL")
        if line.get("time_blockers"):
            blockers.add("TIME_BLOCKER")
        if not line.get("month_boundary_week_complete", True):
            blockers.add("MONTH_BOUNDARY_WEEK_INCOMPLETE")
        if line.get("missing_contract_facts"):
            blockers.add("MISSING_CONTRACT_FACTS")

    return sorted(blockers)


def close_period(*, period: PayrollPeriod, payload: dict, reason: str = "") -> PayrollSnapshot:
    """Close (or reclose) the period. Idempotent while already CLOSED."""
    blockers = collect_blockers(period, payload)
    if blockers:
        raise CloseBlocked(blockers)

    with transaction.atomic():
        locked = PayrollPeriod.objects.select_for_update().get(pk=period.pk)
        latest = PayrollSnapshot.objects.filter(period=locked).order_by("-version").first()
        if locked.status == PeriodStatus.CLOSED and latest is not None:
            return latest  # idempotent: a concurrent close already won

        version = (latest.version if latest is not None else 0) + 1
        snapshot = PayrollSnapshot.objects.create(
            period=locked,
            version=version,
            supersedes=latest,
            reason=reason,
            checksum=checksum_of(payload),
            payload=payload,
        )
        locked.status = PeriodStatus.CLOSED
        locked.save(update_fields=["status", "updated_at"])

    audit.record(
        actor_type="MANAGER",
        actor_id="",
        action="CLOSE",
        subject_type="PayrollPeriod",
        subject_id=f"{period.month:%Y-%m}",
        result="SUCCESS",
        after={"version": version, "checksum": snapshot.checksum},
    )
    return snapshot


def reopen_period(*, period: PayrollPeriod, reason: str) -> PayrollPeriod:
    """Return a closed period to DRAFT for correction. Snapshots are preserved."""
    if not reason.strip():
        raise ValueError("Reopening requires a reason.")
    with transaction.atomic():
        locked = PayrollPeriod.objects.select_for_update().get(pk=period.pk)
        locked.status = PeriodStatus.DRAFT
        locked.save(update_fields=["status", "updated_at"])
    audit.record(
        actor_type="MANAGER",
        actor_id="",
        action="REOPEN",
        subject_type="PayrollPeriod",
        subject_id=f"{period.month:%Y-%m}",
        result="SUCCESS",
    )
    return period


def latest_snapshot(period: PayrollPeriod) -> PayrollSnapshot | None:
    return PayrollSnapshot.objects.filter(period=period).order_by("-version").first()
