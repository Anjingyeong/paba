"""Object-level authorization: managers broad, employees self-only, revoked denied."""

from __future__ import annotations

import pytest

from apps.auditlog.authorization import AuthorizationError, Principal, authorize, require
from apps.identity.models import AccountRole


def test_manager_can_access_any_subject() -> None:
    mgr = Principal(role=AccountRole.MANAGER, actor_id="u1")
    assert authorize(mgr, "VIEW", subject_owner_id="EMP-999") is True
    assert authorize(mgr, "EXPORT", subject_owner_id=None) is True


def test_employee_can_only_touch_own_allowed_subject() -> None:
    emp = Principal(role=AccountRole.EMPLOYEE, actor_id="EMP-1")
    assert authorize(emp, "PUNCH", subject_owner_id="EMP-1") is True
    assert authorize(emp, "REQUEST_CORRECTION", subject_owner_id="EMP-1") is True
    # Another employee's subject:
    assert authorize(emp, "PUNCH", subject_owner_id="EMP-2") is False
    # A manager-only action, even on self:
    assert authorize(emp, "EXPORT", subject_owner_id="EMP-1") is False


def test_revoked_device_denies_even_manager() -> None:
    mgr = Principal(role=AccountRole.MANAGER, actor_id="u1", device_ok=False)
    assert authorize(mgr, "VIEW", subject_owner_id="EMP-1") is False


def test_unknown_role_denied() -> None:
    ghost = Principal(role="GHOST", actor_id="x")
    assert authorize(ghost, "VIEW", subject_owner_id="x") is False


def test_require_raises_when_denied() -> None:
    emp = Principal(role=AccountRole.EMPLOYEE, actor_id="EMP-1")
    with pytest.raises(AuthorizationError):
        require(emp, "PUNCH", subject_owner_id="EMP-2")
