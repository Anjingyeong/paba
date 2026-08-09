"""Employee identity: role vs. compensation-profile independence and date sanity."""

from __future__ import annotations

import datetime as dt

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.identity.models import AccountRole, CompensationProfile, Employee

pytestmark = pytest.mark.django_db


def _employee(**kwargs) -> Employee:
    defaults = {
        "employee_code": "EMP-001",
        "display_name": "합성직원",
        "hire_date": dt.date(2026, 1, 1),
    }
    defaults.update(kwargs)
    return Employee.objects.create(**defaults)


def test_manager_role_can_carry_general_profile() -> None:
    emp = _employee(
        employee_code="MGR-1",
        account_role=AccountRole.MANAGER,
        compensation_profile=CompensationProfile.GENERAL,
    )
    emp.full_clean()
    assert emp.account_role == AccountRole.MANAGER
    assert emp.compensation_profile == CompensationProfile.GENERAL


def test_employee_role_can_carry_manager_profile() -> None:
    emp = _employee(
        employee_code="EMP-2",
        account_role=AccountRole.EMPLOYEE,
        compensation_profile=CompensationProfile.MANAGER,
    )
    emp.full_clean()
    assert emp.account_role == AccountRole.EMPLOYEE
    assert emp.compensation_profile == CompensationProfile.MANAGER


def test_default_role_and_profile() -> None:
    emp = _employee()
    assert emp.account_role == AccountRole.EMPLOYEE
    assert emp.compensation_profile == CompensationProfile.GENERAL


def test_leave_date_before_hire_is_rejected_by_db() -> None:
    with pytest.raises(IntegrityError), transaction.atomic():
        _employee(
            employee_code="EMP-3",
            hire_date=dt.date(2026, 5, 1),
            leave_date=dt.date(2026, 4, 1),
        )


def test_employee_code_cannot_look_like_a_name() -> None:
    emp = Employee(
        employee_code="홍길동",
        display_name="홍길동",
        hire_date=dt.date(2026, 1, 1),
    )
    with pytest.raises(ValidationError):
        emp.full_clean()


def test_employee_code_is_unique() -> None:
    _employee(employee_code="EMP-9")
    with pytest.raises(IntegrityError), transaction.atomic():
        _employee(employee_code="EMP-9", display_name="다른직원")
