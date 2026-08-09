"""Employee correction requests and manager superseding corrections.

Raw punches are immutable. A manager correction records the authoritative corrected
event sequence as a new :class:`ShiftCorrection` that supersedes the previous one;
the original :class:`PunchEvent` rows are never touched. Every request and correction
is written to the audit log, and each carries a non-empty reason.
"""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db.models import Q

from apps.attendance.models import CorrectionRequest, PunchEvent, Shift, ShiftCorrection
from apps.auditlog import services as audit
from apps.auditlog.authorization import AuthorizationError
from apps.identity.models import Employee


def raw_event_state(shift: Shift) -> list[dict]:
    """The immutable raw punch sequence, as serializable dicts."""
    return [
        {"kind": e.kind, "occurred_at": e.occurred_at.isoformat()}
        for e in PunchEvent.objects.filter(shift=shift).order_by("occurred_at", "id")
    ]


def current_correction(shift: Shift) -> ShiftCorrection | None:
    return ShiftCorrection.objects.filter(shift=shift).order_by("-created_at", "-id").first()


def effective_events(shift: Shift) -> list[dict]:
    """The corrected sequence if any correction exists, else the raw punches."""
    latest = current_correction(shift)
    return latest.corrected_events if latest is not None else raw_event_state(shift)


def _owns(employee: Employee, shift: Shift) -> bool:
    return Shift.objects.filter(pk=shift.pk, employee=employee).exists()


def request_correction(*, employee: Employee, shift: Shift, reason: str) -> CorrectionRequest:
    """An employee asks to correct their *own* shift. Reason is mandatory."""
    if not _owns(employee, shift):
        raise AuthorizationError("not permitted")
    if not reason.strip():
        raise ValidationError("A reason is required.")

    req = CorrectionRequest.objects.create(shift=shift, requested_by=employee, reason=reason)
    audit.record(
        actor_type="EMPLOYEE",
        actor_id=employee.employee_code,
        action="REQUEST_CORRECTION",
        subject_type="Shift",
        subject_id=str(shift.pk),
        result="SUCCESS",
    )
    return req


def create_correction(
    *,
    manager,
    shift: Shift,
    corrected_events: list[dict],
    reason: str,
    evidence_note: str = "",
) -> ShiftCorrection:
    """Record a manager's superseding correction. Never mutates raw punches."""
    if not reason.strip():
        raise ValidationError("A reason is required.")

    previous = current_correction(shift)
    before_state = effective_events(shift)
    correction = ShiftCorrection.objects.create(
        shift=shift,
        supersedes=previous,
        actor=manager,
        reason=reason,
        evidence_note=evidence_note,
        corrected_events=corrected_events,
        before_digest=audit.digest_state({"events": before_state}),
        after_digest=audit.digest_state({"events": corrected_events}),
    )
    # Resolve any open employee requests for this shift.
    CorrectionRequest.objects.filter(Q(shift=shift) & Q(resolved_at__isnull=True)).update(
        resolved_at=correction.created_at
    )
    audit.record(
        actor_type="MANAGER",
        actor_id=str(getattr(manager, "pk", "")),
        action="CORRECT",
        subject_type="Shift",
        subject_id=str(shift.pk),
        result="SUCCESS",
        before={"events": before_state},
        after={"events": corrected_events},
    )
    return correction
