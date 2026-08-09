"""Attendance shifts and append-only punch events.

A :class:`Shift` groups the punches of one work session. Each :class:`PunchEvent`
is server-timestamped (Asia/Seoul, never client time), tagged with the kiosk
device and an idempotency key, and appended in a fixed order:

    CLOCK_IN → (BREAK_START → BREAK_END)* → CLOCK_OUT

Invariants enforced at the database level:
- at most one *open* shift per employee (partial unique constraint), and
- idempotency keys are globally unique, so a resent/double-tapped punch collapses
  to a single event.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.devices.models import KioskDevice
from apps.identity.models import Employee


class PunchKind(models.TextChoices):
    CLOCK_IN = "CLOCK_IN", "출근"
    BREAK_START = "BREAK_START", "휴게 시작"
    BREAK_END = "BREAK_END", "휴게 종료"
    CLOCK_OUT = "CLOCK_OUT", "퇴근"


class Shift(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name="shifts")
    opened_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["employee"],
                condition=models.Q(closed_at__isnull=True),
                name="one_open_shift_per_employee",
            ),
        ]

    def __str__(self) -> str:
        return f"Shift#{self.pk} {'open' if self.is_open else 'closed'}"

    @property
    def is_open(self) -> bool:
        return self.closed_at is None


class PunchEvent(models.Model):
    shift = models.ForeignKey(Shift, on_delete=models.PROTECT, related_name="events")
    kind = models.CharField(max_length=16, choices=PunchKind.choices)
    occurred_at = models.DateTimeField()
    device = models.ForeignKey(
        KioskDevice, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    idempotency_key = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["occurred_at", "id"]
        indexes = [models.Index(fields=["shift", "occurred_at"])]

    def __str__(self) -> str:
        return f"PunchEvent#{self.pk} {self.kind}"


class CorrectionRequest(models.Model):
    """An employee-raised request to correct their own shift. Read-only evidence;
    it never mutates punches and carries no payroll data."""

    shift = models.ForeignKey(Shift, on_delete=models.PROTECT, related_name="correction_requests")
    requested_by = models.ForeignKey(
        Employee, on_delete=models.PROTECT, related_name="correction_requests"
    )
    reason = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"CorrectionRequest#{self.pk}"


class ShiftCorrection(models.Model):
    """A manager's superseding correction of a shift.

    Raw :class:`PunchEvent` rows are never edited; instead a correction records the
    authoritative corrected event sequence (``corrected_events``) together with the
    actor, reason, evidence note and before/after digests. ``supersedes`` links to
    the prior correction so the chain only ever grows.
    """

    shift = models.ForeignKey(Shift, on_delete=models.PROTECT, related_name="corrections")
    supersedes = models.ForeignKey(
        "self", on_delete=models.PROTECT, null=True, blank=True, related_name="superseded_by"
    )
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    reason = models.CharField(max_length=500)
    evidence_note = models.CharField(max_length=500, blank=True)
    corrected_events = models.JSONField(default=list)
    before_digest = models.CharField(max_length=64)
    after_digest = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self) -> str:
        return f"ShiftCorrection#{self.pk}"


class ShiftApproval(models.Model):
    """A manager's approval of a shift's current effective state.

    The approval pins the specific correction it approved (``correction``; null =
    raw punches). When a newer correction is added the approval no longer matches
    the current state and is treated as stale until re-approved.
    """

    shift = models.OneToOneField(Shift, on_delete=models.PROTECT, related_name="approval")
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    correction = models.ForeignKey(
        ShiftCorrection, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    approved_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"ShiftApproval#{self.pk}"
