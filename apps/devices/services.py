"""Kiosk pairing lifecycle: issue code → activate device → verify → revoke."""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import timedelta

from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone

from .models import KioskDevice, PairingCode

PAIRING_CODE_TTL = timedelta(minutes=10)


@dataclass(frozen=True)
class ActivationResult:
    device: KioskDevice
    device_secret: str  # cleartext, returned once to set the kiosk cookie


def create_pairing_code(manager: User) -> str:
    """Issue a one-time pairing code; return the cleartext once."""
    code = secrets.token_hex(4)  # 8 hex chars, short enough to type
    PairingCode.objects.create(
        code_hash=make_password(code),
        created_by=manager,
        expires_at=timezone.now() + PAIRING_CODE_TTL,
    )
    return code


@transaction.atomic
def activate_device(code: str, device_name: str) -> ActivationResult | None:
    """Pair a device using a valid, unused, unexpired code. Consumes the code.

    The matched code row is locked with ``select_for_update`` and re-checked, so
    two concurrent activations of the same code cannot both succeed.
    """
    now = timezone.now()
    candidate: PairingCode | None = None
    for row in PairingCode.objects.select_for_update().filter(
        used_at__isnull=True, expires_at__gt=now
    ):
        if check_password(code, row.code_hash):
            candidate = row
            break
    if candidate is None:
        return None

    device_secret = secrets.token_urlsafe(32)
    device = KioskDevice.objects.create(
        name=device_name, secret_hash=make_password(device_secret)
    )
    candidate.used_at = now
    candidate.device = device
    candidate.save(update_fields=["used_at", "device"])
    return ActivationResult(device=device, device_secret=device_secret)


def verify_device(device_id: int | None, device_secret: str | None) -> KioskDevice | None:
    """Return the active device iff the id + secret match and it is not revoked."""
    if not device_id or not device_secret:
        return None
    device = KioskDevice.objects.filter(pk=device_id, revoked_at__isnull=True).first()
    if device is None:
        return None
    if check_password(device_secret, device.secret_hash):
        return device
    return None


def revoke_device(device: KioskDevice) -> None:
    if device.revoked_at is None:
        device.revoked_at = timezone.now()
        device.save(update_fields=["revoked_at"])
