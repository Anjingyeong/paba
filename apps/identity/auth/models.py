"""Authentication secrets: manager TOTP, recovery codes, and employee PINs.

All secrets are stored hashed or encrypted:
- TOTP seeds are symmetrically **encrypted** at rest (reversible — needed to compute
  codes) using the application key.
- Recovery codes and employee PINs are stored as **one-way Argon2id hashes**; the
  cleartext is shown once at issue time and never persisted.

Models are declared with ``app_label = "identity"`` and use string FK references
so this submodule can be imported by ``apps.identity.models`` without cycles.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models


class ManagerTOTP(models.Model):
    """A manager's TOTP authenticator. One per user; required to complete login."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="totp"
    )
    encrypted_secret = models.TextField()
    confirmed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "identity"

    def __str__(self) -> str:
        return f"ManagerTOTP#{self.pk}"

    @property
    def is_confirmed(self) -> bool:
        return self.confirmed_at is not None


class RecoveryCode(models.Model):
    """Single-use manager recovery code, stored as a one-way hash."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="recovery_codes"
    )
    code_hash = models.CharField(max_length=255)
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "identity"

    def __str__(self) -> str:
        return f"RecoveryCode#{self.pk}"

    @property
    def is_used(self) -> bool:
        return self.used_at is not None


class EmployeePin(models.Model):
    """A kiosk PIN for one employee, stored as a one-way Argon2id hash.

    Tracks failed attempts and a lockout window for rate limiting; the cleartext
    6-digit PIN is generated cryptographically and shown to the manager once.
    """

    employee = models.OneToOneField(
        "identity.Employee", on_delete=models.CASCADE, related_name="pin"
    )
    pin_hash = models.CharField(max_length=255)
    failed_attempts = models.PositiveSmallIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "identity"

    def __str__(self) -> str:
        return f"EmployeePin#{self.pk}"
