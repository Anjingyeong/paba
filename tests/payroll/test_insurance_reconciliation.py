"""Insurance reconciliation lifecycle and the all-final close gate."""

from __future__ import annotations

import datetime as dt

import pytest
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from apps.identity.models import Employee
from apps.payroll.models.deductions import InsuranceStatus
from apps.payroll.services.deductions import EMPLOYEE_INSURANCES
from apps.payroll.services.deductions import reconciliation as recon

pytestmark = pytest.mark.django_db

VERSION = "2026.1"
PERIOD = dt.date(2026, 7, 1)


def _emp() -> Employee:
    return Employee.objects.create(
        employee_code="EMP-1", display_name="직원", hire_date=dt.date(2026, 1, 1)
    )


def _mgr() -> User:
    return User.objects.create_user("mgr", password="pw-123456-strong", is_staff=True)


def test_estimate_then_reconcile_records_variance() -> None:
    emp, mgr = _emp(), _mgr()
    recon.set_estimate(
        employee=emp, period_month=PERIOD, insurance="HEALTH", monthly_base=3_000_000,
        version=VERSION,
    )
    obj = recon.reconcile(
        employee=emp, period_month=PERIOD, insurance="HEALTH", final_amount=106_500,
        manager=mgr, reason="기관 고지액 반영",
    )
    assert obj.status == InsuranceStatus.RECONCILED
    assert obj.estimated_amount == 106_350
    assert obj.variance == 150


def test_reconcile_requires_reason() -> None:
    emp, mgr = _emp(), _mgr()
    recon.set_estimate(
        employee=emp, period_month=PERIOD, insurance="HEALTH", monthly_base=3_000_000,
        version=VERSION,
    )
    with pytest.raises(ValidationError):
        recon.reconcile(
            employee=emp, period_month=PERIOD, insurance="HEALTH", final_amount=1,
            manager=mgr, reason="  ",
        )


def test_close_blocked_until_all_four_final() -> None:
    emp, mgr = _emp(), _mgr()
    for ins in EMPLOYEE_INSURANCES:
        recon.set_estimate(
            employee=emp, period_month=PERIOD, insurance=ins, monthly_base=3_000_000,
            version=VERSION,
        )
    # All merely ESTIMATED -> not final.
    assert recon.all_insurances_final(employee=emp, period_month=PERIOD) is False

    recon.reconcile(
        employee=emp, period_month=PERIOD, insurance="NATIONAL_PENSION", final_amount=135_000,
        manager=mgr, reason="ok",
    )
    recon.reconcile(
        employee=emp, period_month=PERIOD, insurance="HEALTH", final_amount=106_350,
        manager=mgr, reason="ok",
    )
    recon.reconcile(
        employee=emp, period_month=PERIOD, insurance="LONG_TERM_CARE", final_amount=13_772,
        manager=mgr, reason="ok",
    )
    # Still one (EMPLOYMENT) estimated -> blocked.
    assert recon.all_insurances_final(employee=emp, period_month=PERIOD) is False

    recon.set_not_applicable(
        employee=emp, period_month=PERIOD, insurance="EMPLOYMENT", manager=mgr, reason="미가입",
    )
    assert recon.all_insurances_final(employee=emp, period_month=PERIOD) is True
