"""Manager TOTP provisioning, verification, recovery codes, and secret secrecy."""

from __future__ import annotations

import pyotp
import pytest
from django.contrib.auth.models import User

from apps.identity.auth import services
from apps.identity.auth.models import ManagerTOTP

pytestmark = pytest.mark.django_db


def _user() -> User:
    return User.objects.create_user("mgr", password="a-strong-password-123456", is_staff=True)


def test_provision_and_confirm_totp() -> None:
    user = _user()
    secret = services.provision_totp(user)
    assert services.has_confirmed_totp(user) is False
    assert services.confirm_totp(user, pyotp.TOTP(secret).now()) is True
    assert services.has_confirmed_totp(user) is True


def test_verify_totp_rejects_wrong_token() -> None:
    user = _user()
    secret = services.provision_totp(user)
    services.confirm_totp(user, pyotp.TOTP(secret).now())
    assert services.verify_totp(user, "000000") is False
    assert services.verify_totp(user, pyotp.TOTP(secret).now()) is True


def test_totp_secret_is_encrypted_at_rest() -> None:
    user = _user()
    secret = services.provision_totp(user)
    stored = ManagerTOTP.objects.get(user=user).encrypted_secret
    assert secret not in stored  # not stored in the clear
    # But the app can still decrypt to compute codes.
    assert services.verify_totp(user, pyotp.TOTP(secret).now()) is True


def test_recovery_code_is_single_use() -> None:
    user = _user()
    codes = services.generate_recovery_codes(user)
    assert len(codes) == 10
    assert services.verify_recovery_code(user, codes[0]) is True
    # Same code cannot be used twice.
    assert services.verify_recovery_code(user, codes[0]) is False
    # A different, unused code still works.
    assert services.verify_recovery_code(user, codes[1]) is True


def test_recovery_codes_hashed_not_plaintext() -> None:
    user = _user()
    codes = services.generate_recovery_codes(user)
    from apps.identity.auth.models import RecoveryCode

    hashes = list(RecoveryCode.objects.filter(user=user).values_list("code_hash", flat=True))
    for code in codes:
        assert code not in hashes


def test_mfa_throttle_locks_after_max_attempts() -> None:
    user = _user()
    assert services.mfa_is_locked(user) is False
    locked = False
    for _ in range(services.MFA_MAX_ATTEMPTS):
        locked = services.mfa_record_failure(user)
    assert locked is True
    assert services.mfa_is_locked(user) is True


def test_mfa_success_clears_throttle() -> None:
    user = _user()
    services.mfa_record_failure(user)
    services.mfa_record_failure(user)
    services.mfa_record_success(user)
    from apps.identity.auth.models import ManagerMfaThrottle

    throttle = ManagerMfaThrottle.objects.get(user=user)
    assert throttle.failed_attempts == 0
    assert throttle.locked_until is None
