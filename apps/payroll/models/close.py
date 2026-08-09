"""Payroll periods and immutable close snapshots.

A :class:`PayrollPeriod` is one Asia/Seoul calendar month. Closing it copies the
fully-resolved payroll into an immutable :class:`PayrollSnapshot` (a versioned,
checksummed JSON payload). Reopening leaves every prior snapshot intact and, on
reclose, a new version is written with ``supersedes`` pointing at the old one.

Immutability is enforced by a model guard and a database trigger that blocks any
UPDATE/DELETE on the snapshot table (added in the migration).
"""

from __future__ import annotations

from django.db import models


class SnapshotImmutableError(Exception):
    """Raised when code attempts to mutate or delete a close snapshot."""


class PeriodStatus(models.TextChoices):
    DRAFT = "DRAFT", "작성"
    CLOSED = "CLOSED", "마감"


class PayrollPeriod(models.Model):
    month = models.DateField(unique=True, help_text="First day of the pay month (Asia/Seoul).")
    status = models.CharField(
        max_length=8, choices=PeriodStatus.choices, default=PeriodStatus.DRAFT
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"PayrollPeriod {self.month:%Y-%m} {self.status}"


class PayrollSnapshot(models.Model):
    period = models.ForeignKey(PayrollPeriod, on_delete=models.PROTECT, related_name="snapshots")
    version = models.PositiveIntegerField()
    supersedes = models.ForeignKey(
        "self", on_delete=models.PROTECT, null=True, blank=True, related_name="superseded_by"
    )
    reason = models.CharField(max_length=255, blank=True)
    checksum = models.CharField(max_length=64)
    payload = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["period", "version"], name="one_snapshot_per_version"),
        ]
        ordering = ["period", "version"]

    def __str__(self) -> str:
        return f"PayrollSnapshot#{self.pk} v{self.version}"

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise SnapshotImmutableError("Close snapshots are immutable; updates are forbidden.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise SnapshotImmutableError("Close snapshots are immutable; deletion is forbidden.")
