"""Per-shift approval that goes stale whenever a newer correction supersedes it.

Approval pins the specific correction it approved (or the raw punches, when none
exists). Creating a later correction leaves the approval pointing at an older state,
so :func:`approval_status` reports it as STALE until a manager re-approves.
"""

from __future__ import annotations

from apps.attendance.models import Shift, ShiftApproval
from apps.auditlog import services as audit

from .corrections import current_correction

PENDING = "PENDING"
APPROVED = "APPROVED"
STALE = "STALE"


def approve_shift(*, manager, shift: Shift) -> ShiftApproval:
    """Approve the shift's current effective state (idempotent per current state)."""
    latest = current_correction(shift)
    approval, _ = ShiftApproval.objects.update_or_create(
        shift=shift,
        defaults={"approved_by": manager, "correction": latest},
    )
    audit.record(
        actor_type="MANAGER",
        actor_id=str(getattr(manager, "pk", "")),
        action="APPROVE",
        subject_type="Shift",
        subject_id=str(shift.pk),
        result="SUCCESS",
    )
    return approval


def approval_status(shift: Shift) -> str:
    approval = ShiftApproval.objects.filter(shift=shift).select_related("correction").first()
    if approval is None:
        return PENDING
    latest = current_correction(shift)
    # Model equality compares pk; None == None is True, instance vs None is False.
    return APPROVED if approval.correction == latest else STALE
