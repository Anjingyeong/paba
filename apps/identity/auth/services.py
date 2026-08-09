"""Authentication services: manager TOTP/recovery and employee PIN verification.

Security properties enforced here:
- PINs are cryptographically generated (``secrets``), Argon2id-hashed, and verified
  in constant-ish time. After ``PIN_MAX_ATTEMPTS`` failures the PIN locks for
  ``PIN_LOCKOUT``; verification of an *unknown* employee performs the same work and
  returns the same result shape, so responses never reveal whether a code exists.
- TOTP secrets are encrypted at rest; codes are checked with a ±1 step window.
- Recovery codes are single-use, stored only as hashes.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import timedelta

import pyotp
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import User
from django.utils import timezone

from apps.core.crypto import decrypt, encrypt
from apps.identity.models import Employee

from .models import EmployeePin, ManagerMfaThrottle, ManagerTOTP, RecoveryCode

PIN_LENGTH = 6
PIN_MAX_ATTEMPTS = 10
PIN_LOCKOUT = timedelta(minutes=15)
RECOVERY_CODE_COUNT = 10
MFA_MAX_ATTEMPTS = 5
MFA_LOCKOUT = timedelta(minutes=15)

# A throwaway Argon2 hash used to spend comparable work when an employee/PIN does
# not exist, so timing and behaviour do not leak existence.
_DUMMY_HASH = make_password("0" * PIN_LENGTH)


@dataclass(frozen=True)
class PinResult:
    ok: bool
    locked: bool = False


# --- Employee PIN -----------------------------------------------------------
def generate_pin() -> str:
    """A cryptographically-random zero-padded numeric PIN."""
    return f"{secrets.randbelow(10**PIN_LENGTH):0{PIN_LENGTH}d}"


def set_employee_pin(employee: Employee, pin: str) -> EmployeePin:
    obj, _ = EmployeePin.objects.get_or_create(
        employee=employee, defaults={"pin_hash": ""}
    )
    obj.pin_hash = make_password(pin)
    obj.failed_attempts = 0
    obj.locked_until = None
    obj.save()
    return obj


def issue_employee_pin(employee: Employee) -> str:
    """Generate, store (hashed) and return a fresh PIN. Caller shows it once."""
    pin = generate_pin()
    set_employee_pin(employee, pin)
    return pin


def reset_employee_pin(employee: Employee) -> str:
    """Manager-initiated PIN reset (clears any lockout)."""
    return issue_employee_pin(employee)


def verify_employee_pin(employee_code: str, pin: str) -> PinResult:
    """Verify a PIN for an employee code. Enumeration- and lockout-safe."""
    now = timezone.now()
    record = (
        EmployeePin.objects.select_related("employee")
        .filter(employee__employee_code=employee_code)
        .first()
    )

    if record is None:
        # Unknown employee: do comparable work, reveal nothing.
        check_password(pin, _DUMMY_HASH)
        return PinResult(ok=False)

    if record.locked_until is not None and record.locked_until > now:
        return PinResult(ok=False, locked=True)

    if check_password(pin, record.pin_hash):
        if record.failed_attempts or record.locked_until:
            record.failed_attempts = 0
            record.locked_until = None
            record.save(update_fields=["failed_attempts", "locked_until", "updated_at"])
        return PinResult(ok=True)

    record.failed_attempts += 1
    locked = record.failed_attempts >= PIN_MAX_ATTEMPTS
    if locked:
        record.locked_until = now + PIN_LOCKOUT
        record.failed_attempts = 0
    record.save(update_fields=["failed_attempts", "locked_until", "updated_at"])
    return PinResult(ok=False, locked=locked)


# --- Manager TOTP -----------------------------------------------------------
def provision_totp(user: User) -> str:
    """Create (unconfirmed) TOTP for a user and return the base32 secret once."""
    secret = pyotp.random_base32()
    ManagerTOTP.objects.update_or_create(
        user=user,
        defaults={"encrypted_secret": encrypt(secret), "confirmed_at": None},
    )
    return secret


def _totp_for(user: User) -> pyotp.TOTP | None:
    totp = ManagerTOTP.objects.filter(user=user).first()
    if totp is None:
        return None
    return pyotp.TOTP(decrypt(totp.encrypted_secret))


def confirm_totp(user: User, token: str) -> bool:
    totp_model = ManagerTOTP.objects.filter(user=user).first()
    if totp_model is None:
        return False
    if pyotp.TOTP(decrypt(totp_model.encrypted_secret)).verify(token, valid_window=1):
        totp_model.confirmed_at = timezone.now()
        totp_model.save(update_fields=["confirmed_at"])
        return True
    return False


def verify_totp(user: User, token: str) -> bool:
    totp = _totp_for(user)
    if totp is None:
        return False
    return totp.verify(token, valid_window=1)


def has_confirmed_totp(user: User) -> bool:
    totp = ManagerTOTP.objects.filter(user=user).first()
    return bool(totp and totp.is_confirmed)


# --- Manager MFA throttling -------------------------------------------------
def mfa_is_locked(user: User) -> bool:
    """Whether the TOTP step is currently locked out for this manager."""
    throttle = ManagerMfaThrottle.objects.filter(user=user).first()
    return bool(
        throttle
        and throttle.locked_until is not None
        and throttle.locked_until > timezone.now()
    )


def mfa_record_failure(user: User) -> bool:
    """Record a failed MFA attempt; returns True once the account locks."""
    throttle, _ = ManagerMfaThrottle.objects.get_or_create(user=user)
    throttle.failed_attempts += 1
    locked = throttle.failed_attempts >= MFA_MAX_ATTEMPTS
    if locked:
        throttle.locked_until = timezone.now() + MFA_LOCKOUT
        throttle.failed_attempts = 0
    throttle.save(update_fields=["failed_attempts", "locked_until", "updated_at"])
    return locked


def mfa_record_success(user: User) -> None:
    """Clear any throttle state after a successful MFA."""
    ManagerMfaThrottle.objects.filter(user=user).update(failed_attempts=0, locked_until=None)


# --- Recovery codes ---------------------------------------------------------
def generate_recovery_codes(user: User) -> list[str]:
    """Replace a user's recovery codes; return the cleartext set once."""
    RecoveryCode.objects.filter(user=user).delete()
    codes = [f"{secrets.token_hex(4)}" for _ in range(RECOVERY_CODE_COUNT)]
    RecoveryCode.objects.bulk_create(
        RecoveryCode(user=user, code_hash=make_password(code)) for code in codes
    )
    return codes


def verify_recovery_code(user: User, code: str) -> bool:
    """Consume a single-use recovery code if it matches an unused one."""
    for record in RecoveryCode.objects.filter(user=user, used_at__isnull=True):
        if check_password(code, record.code_hash):
            record.used_at = timezone.now()
            record.save(update_fields=["used_at"])
            return True
    return False
