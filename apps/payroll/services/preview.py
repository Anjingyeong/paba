from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.db import transaction
from django.db.backends.postgresql.psycopg_any import DateRange
from django.db.models import Q
from django.utils import timezone

from apps.attendance.models import Shift
from apps.attendance.services.corrections import effective_events
from apps.attendance.services.time_calculation import calculate
from apps.exports.statement import LineItem, StatementData
from apps.identity.models import Employee
from apps.payroll.models import HourlyWage
from apps.payroll.services.earnings import RatedSegment, calculate_base_pay


class PayrollMonthError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class MonthlyPayrollLine:
    employee_code: str
    display_name: str
    total_hours: Decimal
    hourly_wage: int | None
    gross_pay: int
    blockers: tuple[str, ...]

    @property
    def ready(self) -> bool:
        return not self.blockers


def parse_month(value: str) -> date:
    """Parse YYYY-MM, defaulting to the current local month."""
    if not value:
        return timezone.localdate().replace(day=1)
    try:
        return date.fromisoformat(f"{value}-01")
    except ValueError as exc:
        raise PayrollMonthError(value) from exc


def _next_month(month: date) -> date:
    if month.month == 12:
        return date(month.year + 1, 1, 1)
    return date(month.year, month.month + 1, 1)


def _month_bounds(month: date) -> tuple[datetime, datetime]:
    start = timezone.make_aware(datetime.combine(month, time.min))
    end = timezone.make_aware(datetime.combine(_next_month(month), time.min))
    return start, end


def monthly_payroll_lines(month: date) -> list[MonthlyPayrollLine]:
    month = month.replace(day=1)
    month_start, month_end = _month_bounds(month)
    employees = Employee.objects.filter(hire_date__lt=_next_month(month)).filter(
        Q(leave_date__isnull=True) | Q(leave_date__gte=month)
    )
    lines: list[MonthlyPayrollLine] = []

    for employee in employees.order_by("employee_code"):
        wage_at_start = (
            HourlyWage.objects.filter(employee=employee, effective__contains=month)
            .order_by("-pk")
            .first()
        )
        shifts = (
            Shift.objects.filter(
                employee=employee,
                events__occurred_at__gte=month_start,
                events__occurred_at__lt=month_end,
            )
            .distinct()
            .order_by("opened_at", "pk")
        )
        blockers: set[str] = set()
        rated_segments: list[RatedSegment] = []
        total_hours = Decimal(0)

        for shift in shifts:
            result = calculate(effective_events(shift))
            blockers.update(result.blockers)
            for segment in result.segments:
                if not month_start <= segment.start < month_end:
                    continue
                total_hours += segment.hours
                work_date = timezone.localtime(segment.start).date()
                wage = (
                    HourlyWage.objects.filter(employee=employee, effective__contains=work_date)
                    .values_list("hourly_wage", flat=True)
                    .first()
                )
                if wage is None:
                    blockers.add("MISSING_HOURLY_WAGE")
                    continue
                rated_segments.append(RatedSegment(hours=segment.hours, hourly_wage=wage))

        if wage_at_start is None:
            blockers.add("MISSING_HOURLY_WAGE")
        gross_pay = calculate_base_pay(rated_segments).amount_krw if rated_segments else 0
        lines.append(
            MonthlyPayrollLine(
                employee_code=employee.employee_code,
                display_name=employee.display_name,
                total_hours=total_hours,
                hourly_wage=wage_at_start.hourly_wage if wage_at_start is not None else None,
                gross_pay=gross_pay,
                blockers=tuple(sorted(blockers)),
            )
        )

    return lines


def set_hourly_wage(employee: Employee, month: date, amount: int) -> HourlyWage:
    """Set the wage from the selected month without rewriting earlier months."""
    month = month.replace(day=1)
    with transaction.atomic():
        active = (
            HourlyWage.objects.select_for_update()
            .filter(employee=employee, effective__contains=month)
            .first()
        )
        if active is None:
            return HourlyWage.objects.create(
                employee=employee,
                hourly_wage=amount,
                effective=DateRange(month, None),
            )
        if active.effective.lower == month:
            active.hourly_wage = amount
            active.save(update_fields=["hourly_wage", "updated_at"])
            return active

        previous_end = active.effective.upper
        active.effective = DateRange(active.effective.lower, month)
        active.save(update_fields=["effective", "updated_at"])
        return HourlyWage.objects.create(
            employee=employee,
            hourly_wage=amount,
            effective=DateRange(month, previous_end),
        )


def statement_from_line(
    line: MonthlyPayrollLine,
    month: date,
    checksum: str,
) -> StatementData:
    pay_date = _next_month(month) - timedelta(days=1)
    return StatementData(
        attribution_month=month,
        employee_id=line.employee_code,
        department="매장",
        title="직원",
        pay_date=pay_date,
        calc_period=f"{month:%Y-%m}",
        earnings=[LineItem("기본급", line.gross_pay)],
        deductions=[],
        detail_lines=[f"기본급: {line.total_hours:.2f}시간 × 등록 시급"],
        version=1,
        checksum=checksum,
    )
