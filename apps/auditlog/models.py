"""Append-only audit log and legal holds.

Every privileged read, change, export or purge is recorded as one immutable
:class:`AuditLogEntry`. Immutability is enforced at two layers:

1. The model refuses to update an existing row or delete any row.
2. A database trigger (added in the initial migration) raises on any UPDATE or
   DELETE, so even raw ``QuerySet.update()/delete()`` or direct SQL cannot mutate
   history.

Subjects are referenced by an opaque ``(subject_type, subject_id)`` pair, never by
name. ``before_digest``/``after_digest`` are SHA-256 hashes of the redacted state,
so the log proves *that* something changed without storing the sensitive payload.
"""

from __future__ import annotations

from django.db import models


class AuditImmutableError(Exception):
    """Raised when code attempts to mutate or delete an audit entry."""


class AuditLogEntry(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    request_id = models.CharField(max_length=36, blank=True)

    actor_type = models.CharField(max_length=16)  # MANAGER | EMPLOYEE | SYSTEM
    actor_id = models.CharField(max_length=64, blank=True)  # opaque

    action = models.CharField(max_length=64)  # e.g. VIEW, UPDATE, EXPORT, PURGE
    subject_type = models.CharField(max_length=64)
    subject_id = models.CharField(max_length=64)  # opaque

    result = models.CharField(max_length=16)  # SUCCESS | DENIED | ERROR
    before_digest = models.CharField(max_length=64, blank=True)
    after_digest = models.CharField(max_length=64, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["subject_type", "subject_id"]),
            models.Index(fields=["actor_type", "actor_id"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return f"AuditLogEntry#{self.pk} {self.action} {self.result}"

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise AuditImmutableError("Audit entries are append-only; updates are forbidden.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise AuditImmutableError("Audit entries are append-only; deletion is forbidden.")


class LegalHold(models.Model):
    """A hold that exempts a subject from retention purges until released."""

    subject_type = models.CharField(max_length=64)
    subject_id = models.CharField(max_length=64)
    reason = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    released_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["subject_type", "subject_id"],
                condition=models.Q(released_at__isnull=True),
                name="one_active_hold_per_subject",
            ),
        ]

    def __str__(self) -> str:
        return f"LegalHold({self.subject_type}:{self.subject_id})"

    @property
    def is_active(self) -> bool:
        return self.released_at is None
