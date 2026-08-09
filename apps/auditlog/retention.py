"""Retention and destruction of personal data.

Departed employees' personal data is destroyed only after a retention window that
covers the legal minimum for payroll/attendance evidence **and** a backup-expiry
grace period, and only when no legal hold is active for that subject. The purge is
idempotent and records a completion entry (a ``PURGE`` audit row) for each subject
it destroys. A dry run reports candidates and writes nothing.

Audit entries themselves are never purged here — they are append-only and retained
on their own (longer) schedule.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from django.db import transaction
from django.utils import timezone

from apps.identity.models import Employee

from . import services
from .models import LegalHold

# Legal minimum for payroll/attendance evidence (3y) plus backup-expiry grace.
EMPLOYEE_PII_RETENTION = timedelta(days=365 * 3)
BACKUP_GRACE = timedelta(days=35)
SUBJECT_TYPE = "Employee"


@dataclass(frozen=True)
class PurgeReport:
    dry_run: bool
    candidates: list[str]  # employee codes
    purged: int


def _cutoff(today: date) -> date:
    return today - (EMPLOYEE_PII_RETENTION + BACKUP_GRACE)


def _has_active_hold(subject_id: str) -> bool:
    return LegalHold.objects.filter(
        subject_type=SUBJECT_TYPE, subject_id=subject_id, released_at__isnull=True
    ).exists()


def find_candidates(today: date | None = None) -> list[Employee]:
    today = today or timezone.localdate()
    cutoff = _cutoff(today)
    departed = Employee.objects.filter(leave_date__isnull=False, leave_date__lte=cutoff)
    return [e for e in departed if not _has_active_hold(e.employee_code)]


def purge_expired(*, dry_run: bool = True, today: date | None = None) -> PurgeReport:
    candidates = find_candidates(today)
    codes = [e.employee_code for e in candidates]
    if dry_run:
        return PurgeReport(dry_run=True, candidates=codes, purged=0)

    purged = 0
    for employee in candidates:
        code = employee.employee_code
        with transaction.atomic():
            employee.delete()
            services.record(
                actor_type="SYSTEM",
                actor_id="retention",
                action="PURGE",
                subject_type=SUBJECT_TYPE,
                subject_id=code,
                result="SUCCESS",
            )
        purged += 1
    return PurgeReport(dry_run=False, candidates=codes, purged=purged)
