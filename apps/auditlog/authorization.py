"""Object-level authorization for a single-store deployment.

Rules are intentionally small and explicit:

- A **MANAGER** may act on any subject in the store.
- An **EMPLOYEE** may only act on subjects they *own* (their own shift, their own
  correction request) and only with employee-safe actions. They can never read the
  employee roster, other employees' data, or any payroll figures.
- Anything else (unknown actor, revoked kiosk device) is denied.

Callers pass the acting principal and the subject's owner id; the function returns
a boolean and never leaks *why* access was denied.
"""

from __future__ import annotations

from dataclasses import dataclass

from apps.identity.models import AccountRole

# Actions an employee is ever allowed to perform, and only on their own subjects.
EMPLOYEE_SELF_ACTIONS = frozenset(
    {"PUNCH", "VIEW_OWN_SHIFT", "REQUEST_CORRECTION", "UNLOCK"}
)


@dataclass(frozen=True)
class Principal:
    role: str  # AccountRole value, or "SYSTEM"
    actor_id: str  # opaque employee id / user id
    device_ok: bool = True  # False when the kiosk device is revoked/unpaired


def authorize(principal: Principal, action: str, subject_owner_id: str | None) -> bool:
    if not principal.device_ok:
        return False
    if principal.role == AccountRole.MANAGER:
        return True
    if principal.role == AccountRole.EMPLOYEE:
        return (
            action in EMPLOYEE_SELF_ACTIONS
            and subject_owner_id is not None
            and subject_owner_id == principal.actor_id
        )
    return False


class AuthorizationError(Exception):
    """Raised by services when an action is not permitted."""


def require(principal: Principal, action: str, subject_owner_id: str | None) -> None:
    if not authorize(principal, action, subject_owner_id):
        raise AuthorizationError("not permitted")
