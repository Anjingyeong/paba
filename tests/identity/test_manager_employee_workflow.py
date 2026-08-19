from __future__ import annotations

import datetime as dt

import pytest
from django.contrib.auth.models import User
from django.test import Client

from apps.identity.auth.middleware import stamp_login
from apps.identity.auth.services import verify_employee_pin
from apps.identity.models import Employee
from apps.payroll.models import HourlyWage

pytestmark = pytest.mark.django_db


def _manager_client() -> Client:
    manager = User.objects.create_user("employee-manager", is_staff=True)
    client = Client()
    client.force_login(manager)
    session = client.session
    stamp_login(session)
    session.save()
    return client


def test_manager_creates_employee_with_initial_wage_and_pin() -> None:
    response = _manager_client().post(
        "/manager/employees/create/",
        {
            "employee_code": "emp-101",
            "display_name": "신규 직원",
            "hire_date": "2026-01-01",
            "hourly_wage": "12000",
            "pin": "246810",
        },
    )

    assert response.status_code == 302
    employee = Employee.objects.get(employee_code="EMP-101")
    wage = HourlyWage.objects.get(employee=employee)
    assert wage.hourly_wage == 12_000
    assert wage.effective.lower == dt.date(2026, 1, 1)
    assert verify_employee_pin("EMP-101", "246810").ok is True


def test_manager_creates_manual_payroll_employee_without_pin() -> None:
    response = _manager_client().post(
        "/manager/employees/create/",
        {
            "employee_code": "emp-103",
            "display_name": "수기 급여 직원",
            "hire_date": "2026-01-01",
            "hourly_wage": "13000",
        },
    )

    assert response.status_code == 302
    employee = Employee.objects.get(employee_code="EMP-103")
    wage = HourlyWage.objects.get(employee=employee)
    assert wage.hourly_wage == 13_000
    assert verify_employee_pin("EMP-103", "000000").ok is False


def test_departed_employee_can_no_longer_unlock_kiosk() -> None:
    client = _manager_client()
    create = client.post(
        "/manager/employees/create/",
        {
            "employee_code": "EMP-102",
            "display_name": "퇴사 직원",
            "hire_date": "2025-01-01",
            "hourly_wage": "12000",
            "pin": "135790",
        },
    )
    assert create.status_code == 302

    response = client.post(
        "/manager/employees/EMP-102/terminate/",
        {"leave_date": "2025-12-31"},
    )

    assert response.status_code == 302
    employee = Employee.objects.get(employee_code="EMP-102")
    assert employee.leave_date == dt.date(2025, 12, 31)
    assert verify_employee_pin("EMP-102", "135790").ok is False