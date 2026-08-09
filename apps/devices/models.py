"""Paired kiosk devices and one-time pairing codes.

A store tablet is *paired* once via a short-lived, one-time code issued by a
manager. Pairing mints a long random device secret: the server keeps only its
Argon2id hash, and the device keeps the cleartext in a ``__Host-kiosk`` cookie
(Secure/HttpOnly/SameSite=Strict). Devices are revocable; a revoked device can no
longer unlock the kiosk.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models


class KioskDevice(models.Model):
    name = models.CharField(max_length=60)
    secret_hash = models.CharField(max_length=255)
    paired_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"KioskDevice#{self.pk} {self.name}"

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None


class PairingCode(models.Model):
    """A single-use, short-lived code that authorizes pairing one device."""

    code_hash = models.CharField(max_length=255)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    device = models.ForeignKey(
        KioskDevice, on_delete=models.SET_NULL, null=True, blank=True, related_name="pairing_code"
    )

    def __str__(self) -> str:
        return f"PairingCode#{self.pk}"

    @property
    def is_used(self) -> bool:
        return self.used_at is not None
