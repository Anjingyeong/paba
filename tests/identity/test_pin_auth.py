"""Employee kiosk PIN: entropy, hashing, lockout, and enumeration safety."""

from __future__ import annotations

import datetime as dt

import pytest

from apps.identity.auth import services
from apps.identity.auth.models import EmployeePin
from apps.identity.models import Employee

pytestmark = pytest.mark.django_db


def _employee(code: str = "EMP-001") -> Employee:
    return Employee.objects.create(
        employee_code=code, display_name="합성직원", hire_date=dt.date(2026, 1, 1)
    )


def test_generated_pin_is_six_digits() -> None:
    for _ in range(50):
        pin = services.generate_pin()
        assert len(pin) == 6
        assert pin.isdigit()


def test_generated_pins_vary() -> None:
    assert len({services.generate_pin() for _ in range(200)}) > 50


def test_pin_is_hashed_not_stored_plaintext() -> None:
    emp = _employee()
    pin = services.issue_employee_pin(emp)
    record = EmployeePin.objects.get(employee=emp)
    assert pin not in record.pin_hash
    assert record.pin_hash.startswith("argon2")


def test_set_and_verify_pin() -> None:
    emp = _employee()
    services.set_employee_pin(emp, "123456")
    assert services.verify_employee_pin("EMP-001", "123456").ok is True
    assert services.verify_employee_pin("EMP-001", "000000").ok is False


def test_lockout_after_ten_failures() -> None:
    emp = _employee()
    services.set_employee_pin(emp, "123456")
    result = None
    for _ in range(10):
        result = services.verify_employee_pin("EMP-001", "999999")
    assert result is not None and result.locked is True
    # Correct PIN is refused while locked.
    assert services.verify_employee_pin("EMP-001", "123456").ok is False


def test_unknown_employee_is_enumeration_safe() -> None:
    # No employee/PIN exists: returns a normal negative result, never raises or
    # signals existence.
    result = services.verify_employee_pin("NO-SUCH-EMP", "123456")
    assert result.ok is False
    assert result.locked is False


def test_reset_clears_lockout() -> None:
    emp = _employee()
    services.set_employee_pin(emp, "123456")
    for _ in range(10):
        services.verify_employee_pin("EMP-001", "999999")
    new_pin = services.reset_employee_pin(emp)
    assert services.verify_employee_pin("EMP-001", new_pin).ok is True
