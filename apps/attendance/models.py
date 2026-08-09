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
