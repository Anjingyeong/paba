from __future__ import annotations

from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.backends.postgresql.psycopg_any import DateRange
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.identity.auth.services import issue_employee_pin, set_employee_pin
from apps.identity.models import Employee
from apps.payroll.models import HourlyWage


def _staff_only(request: HttpRequest) -> HttpResponse | None:
    if not isinstance(request.user, User) or not request.user.is_staff:
        return HttpResponseForbidden("접근 권한이 없습니다.")
    return None


def _console_redirect(fragment: str = "employees") -> HttpResponse:
    return redirect(f"/manager/console/#{fragment}")


def _parse_date(raw: str, field_name: str) -> date:
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise ValidationError(f"{field_name} 날짜를 확인해주세요.") from exc


def _validate_pin(pin: str) -> str:
    value = pin.strip()
    if len(value) != 6 or not value.isdecimal():
        raise ValidationError("PIN은 숫자 6자리여야 합니다.")
    return value


@login_required
@require_POST
def create_employee(request: HttpRequest) -> HttpResponse:
    denied = _staff_only(request)
    if denied is not None:
        return denied

    try:
        employee_code = request.POST.get("employee_code", "").strip().upper()
        display_name = request.POST.get("display_name", "").strip()
        hire_date = _parse_date(request.POST.get("hire_date", ""), "입사일")
        hourly_wage = int(request.POST.get("hourly_wage", ""))
        raw_pin = request.POST.get("pin", "").strip()
        pin = _validate_pin(raw_pin) if raw_pin else ""
        if hourly_wage <= 0:
            raise ValidationError("시급은 0보다 커야 합니다.")
        if not display_name:
            raise ValidationError("이름을 입력해주세요.")

        with transaction.atomic():
            employee = Employee(
                employee_code=employee_code,
                display_name=display_name,
                hire_date=hire_date,
            )
            employee.full_clean()
            employee.save()
            if pin:
                set_employee_pin(employee, pin)
            HourlyWage.objects.create(
                employee=employee,
                hourly_wage=hourly_wage,
                effective=DateRange(hire_date, None),
            )
    except (ValidationError, ValueError, IntegrityError) as exc:
        messages.error(request, str(exc))
        return _console_redirect()

    messages.success(request, f"{display_name} 직원을 등록했습니다.")
    return _console_redirect()


@login_required
@require_POST
def reset_employee_pin(request: HttpRequest, employee_code: str) -> HttpResponse:
    denied = _staff_only(request)
    if denied is not None:
        return denied
    employee = get_object_or_404(Employee, employee_code=employee_code)
    pin = issue_employee_pin(employee)
    messages.success(
        request,
        (
            f"{employee.display_name}의 새 PIN은 {pin} 입니다. "
            "이 화면을 닫기 전에 직원에게 전달해주세요."
        ),
    )
    return _console_redirect()


@login_required
@require_POST
def terminate_employee(request: HttpRequest, employee_code: str) -> HttpResponse:
    denied = _staff_only(request)
    if denied is not None:
        return denied
    employee = get_object_or_404(Employee, employee_code=employee_code)
    raw_leave_date = request.POST.get("leave_date", "").strip()
    try:
        leave_date = (
            _parse_date(raw_leave_date, "퇴사일")
            if raw_leave_date
            else timezone.localdate()
        )
        if leave_date < employee.hire_date:
            raise ValidationError("퇴사일은 입사일보다 빠를 수 없습니다.")
    except ValidationError as exc:
        messages.error(request, str(exc))
        return _console_redirect()

    employee.leave_date = leave_date
    employee.full_clean()
    employee.save(update_fields=["leave_date", "updated_at"])
    messages.success(
        request,
        f"{employee.display_name}의 퇴사일을 {leave_date:%Y-%m-%d}로 저장했습니다.",
    )
    return _console_redirect()