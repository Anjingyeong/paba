"""Retention: dry-run writes nothing, legal hold protects, confirmed purge records."""

from __future__ import annotations

import datetime as dt

import pytest
from django.utils import timezone

from apps.auditlog.models import AuditLogEntry, LegalHold
from apps.auditlog.retention import BACKUP_GRACE, EMPLOYEE_PII_RETENTION, purge_expired
from apps.identity.models import Employee

pytestmark = pytest.mark.django_db


def _expired_leave_date() -> dt.date:
    return timezone.localdate() - (EMPLOYEE_PII_RETENTION + BACKUP_GRACE + dt.timedelta(days=1))


def _departed(code: str = "EMP-OLD") -> Employee:
    return Employee.objects.create(
        employee_code=code,
        display_name="합성퇴사자",
        hire_date=dt.date(2019, 1, 1),
        leave_date=_expired_leave_date(),
    )


def test_dry_run_lists_candidates_but_writes_nothing() -> None:
    emp = _departed()
    report = purge_expired(dry_run=True)
    assert emp.employee_code in report.candidates
    assert report.purged == 0
    assert Employee.objects.filter(pk=emp.pk).exists()  # not deleted
    assert AuditLogEntry.objects.filter(action="PURGE").count() == 0


def test_confirmed_purge_destroys_and_records_completion() -> None:
    emp = _departed()
    report = purge_expired(dry_run=False)
    assert report.purged == 1
    assert not Employee.objects.filter(pk=emp.pk).exists()
    audit = AuditLogEntry.objects.get(action="PURGE", subject_id=emp.employee_code)
    assert audit.result == "SUCCESS"
    assert audit.actor_type == "SYSTEM"


def test_legal_hold_protects_from_purge() -> None:
    emp = _departed()
    LegalHold.objects.create(
        subject_type="Employee", subject_id=emp.employee_code, reason="분쟁"
    )
    report = purge_expired(dry_run=False)
    assert emp.employee_code not in report.candidates
    assert report.purged == 0
    assert Employee.objects.filter(pk=emp.pk).exists()


def test_recently_departed_is_retained() -> None:
    emp = Employee.objects.create(
        employee_code="EMP-RECENT",
        display_name="최근퇴사자",
        hire_date=dt.date(2024, 1, 1),
        leave_date=timezone.localdate() - dt.timedelta(days=200),
    )
    report = purge_expired(dry_run=True)
    assert emp.employee_code not in report.candidates
