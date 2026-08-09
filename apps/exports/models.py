"""Export manifest: a durable record of each generated payroll export.

Records which snapshot/version/checksum was exported, by whom, its status, and a
short (5-minute) expiry for the private download. The actual private-object URL is
issued by the storage layer (Todo 16); here we keep the authoritative metadata.
"""

from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.payroll.models.close import PayrollSnapshot

DOWNLOAD_TTL = timedelta(minutes=5)


class ExportStatus(models.TextChoices):
    READY = "READY", "생성완료"
    EXPIRED = "EXPIRED", "만료"


class ExportManifest(models.Model):
    snapshot = models.ForeignKey(PayrollSnapshot, on_delete=models.PROTECT, related_name="exports")
    version = models.PositiveIntegerField()
    checksum = models.CharField(max_length=64)
    status = models.CharField(
        max_length=8, choices=ExportStatus.choices, default=ExportStatus.READY
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+"
    )
    manifest = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def __str__(self) -> str:
        return f"ExportManifest#{self.pk} v{self.version}"

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + DOWNLOAD_TTL
        super().save(*args, **kwargs)

    @property
    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at
