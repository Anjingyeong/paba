"""An employee cannot act on another employee's shift (IDOR)."""

from __future__ import annotations

import datetime as dt

import pytest

from apps.attendance.models import CorrectionRequest, PunchKind
from apps.attendance.services import corrections
from apps.attendance.services.punches import record_punch
from apps.auditlog.authorization import AuthorizationError
from apps.identity.models import Employee

pytestmark = pytest.mark.django_db


def _emp(code: str) -> Employee:
    return Employee.objects.create(
        employee_code=code, display_name="직원", hire_date=dt.date(2026, 1, 1)
    )


def test_cross_employee_correction_request_denied_and_not_recorded() -> None:
    owner = _emp("EMP-OWNER")
    attacker = _emp("EMP-ATTACKER")
    shift = record_punch(
        employee=owner, kind=PunchKind.CLOCK_IN, idempotency_key="in"
    ).shift

    with pytest.raises(AuthorizationError):
        corrections.request_correction(employee=attacker, shift=shift, reason="침해")

    # Denied action created no request row.
    assert CorrectionRequest.objects.count() == 0
