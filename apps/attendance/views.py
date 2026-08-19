"""Kiosk punch endpoint.

Accepts a single punch only from a paired device that also presents a valid,
unexpired one-shot action token (minted by ``/kiosk/unlock/`` in Todo 4). The
token is consumed on success, so the employee never holds a durable session and
each unlock authorizes exactly one action.
"""

from __future__ import annotations

from calendar import Calendar
from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

from django.conf import settings
from django.contrib.auth.models import User
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.http import require_POST

from apps.core.models import Store
from apps.devices.views import KIOSK_ACTION_TOKEN_KEY, device_from_request
from apps.identity.models import Employee
from apps.payroll.models import PayrollPeriod
from apps.payroll.services.close import latest_snapshot
from apps.payroll.services.preview import monthly_payroll_lines, parse_month

from .manager_views import manager_attendance_rows
from .services.punches import InvalidPunch, record_punch


def manager_console(request: HttpRequest) -> HttpResponse:
    if not isinstance(request.user, User) or not request.user.is_staff:
        return HttpResponseForbidden("접근 권한이 없습니다.")
    selected_month = parse_month(request.GET.get("month", ""))
    payroll_rows = monthly_payroll_lines(selected_month)
    employee_rows = list(Employee.objects.order_by("leave_date", "employee_code"))
    selected_employee_code = request.GET.get("employee", "").strip()
    selected_employee = next(
        (
            employee
            for employee in employee_rows
            if employee.employee_code == selected_employee_code
        ),
        None,
    )
    if selected_employee is None:
        selected_employee = next(
            (employee for employee in employee_rows if employee.leave_date is None),
            employee_rows[0] if employee_rows else None,
        )

    raw_week = request.GET.get("week", "").strip()
    try:
        week_anchor = date.fromisoformat(raw_week) if raw_week else selected_month
    except ValueError:
        week_anchor = selected_month
    week_start = week_anchor - timedelta(days=week_anchor.weekday())
    weekday_names = ("월", "화", "수", "목", "금", "토", "일")
    raw_focus = request.GET.get("focus", "").strip()
    try:
        focus_date = date.fromisoformat(raw_focus) if raw_focus else None
    except ValueError:
        focus_date = None
    week_days = [
        {
            "index": index,
            "date": week_start + timedelta(days=index),
            "name": weekday_names[index],
            "start_value": "",
            "end_value": "",
            "is_focus": focus_date == week_start + timedelta(days=index),
        }
        for index in range(7)
    ]

    all_attendance_rows = manager_attendance_rows()
    copied_previous_week = False
    if selected_employee is not None and request.GET.get("copy_previous") == "1":
        previous_week_start = week_start - timedelta(days=7)
        for row in all_attendance_rows:
            if row["employee"].pk != selected_employee.pk or row["ended_at"] is None:
                continue
            work_date = timezone.localdate(row["started_at"])
            if not previous_week_start <= work_date < week_start:
                continue
            index = (work_date - previous_week_start).days
            target = week_days[index]
            if target["start_value"]:
                continue
            target["start_value"] = timezone.localtime(row["started_at"]).strftime("%H:%M")
            target["end_value"] = timezone.localtime(row["ended_at"]).strftime("%H:%M")
            copied_previous_week = True

    attendance_rows = all_attendance_rows
    if selected_employee is not None:
        attendance_rows = [
            row
            for row in attendance_rows
            if row["employee"].pk == selected_employee.pk
            and row["started_at"].year == selected_month.year
            and row["started_at"].month == selected_month.month
        ]
    else:
        attendance_rows = []
    selected_payroll_row = (
        next(
            (row for row in payroll_rows if row.employee_code == selected_employee.employee_code),
            None,
        )
        if selected_employee is not None
        else None
    )

    attendance_by_date: dict[date, dict] = {}
    for row in attendance_rows:
        work_date = timezone.localdate(row["started_at"])
        summary = attendance_by_date.setdefault(
            work_date,
            {"hours": Decimal(0), "shift_ids": []},
        )
        if row.get("worked_hours") is not None:
            summary["hours"] += row["worked_hours"]
        summary["shift_ids"].append(row["shift_id"])

    calendar_weeks: list[list[dict]] = []
    employee_code = selected_employee.employee_code if selected_employee is not None else ""
    month_value = selected_month.strftime("%Y-%m")
    for calendar_week in Calendar(firstweekday=0).monthdatescalendar(
        selected_month.year, selected_month.month
    ):
        week_cells: list[dict] = []
        for day_value in calendar_week:
            in_month = day_value.month == selected_month.month
            summary = attendance_by_date.get(day_value) if in_month else None
            week_anchor = day_value - timedelta(days=day_value.weekday())
            if summary is not None and summary["shift_ids"]:
                href = f"#record-{summary['shift_ids'][0]}"
            elif in_month and employee_code:
                href = (
                    f"?month={month_value}&employee={employee_code}"
                    f"&week={week_anchor.isoformat()}&focus={day_value.isoformat()}#quick-entry"
                )
            else:
                href = ""
            week_cells.append(
                {
                    "date": day_value,
                    "in_month": in_month,
                    "hours": summary["hours"] if summary is not None else Decimal(0),
                    "shift_count": len(summary["shift_ids"]) if summary is not None else 0,
                    "href": href,
                }
            )
        calendar_weeks.append(week_cells)
    store = Store.get()
    payroll_period = PayrollPeriod.objects.filter(month=selected_month).first()
    payroll_snapshot = latest_snapshot(payroll_period) if payroll_period is not None else None
    return render(
        request,
        "manager/console.html",
        {
            "attendance_rows": attendance_rows,
            "selected_month": selected_month,
            "employee_rows": employee_rows,
            "selected_employee": selected_employee,
            "selected_payroll_row": selected_payroll_row,
            "calendar_weeks": calendar_weeks,
            "week_start": week_start,
            "week_days": week_days,
            "copied_previous_week": copied_previous_week,
            "manual_entry_batch_id": uuid4(),
            "store": store,
            "payroll_rows": payroll_rows,
            "payroll_period": payroll_period,
            "payroll_snapshot": payroll_snapshot,
            "payroll_export_ready": payroll_period is not None
            and payroll_period.status == "CLOSED"
            and payroll_snapshot is not None,
        },
    )


@require_POST
def kiosk_punch(request: HttpRequest) -> JsonResponse:
    device = device_from_request(request)
    if device is None and not settings.DEBUG:
        return JsonResponse({"ok": False, "error": "unpaired"}, status=403)

    token = request.session.get(KIOSK_ACTION_TOKEN_KEY)
    if not token:
        return JsonResponse({"ok": False, "error": "locked"}, status=401)
    expires_at = parse_datetime(token.get("expires_at", ""))
    if expires_at is None or expires_at < timezone.now():
        request.session.pop(KIOSK_ACTION_TOKEN_KEY, None)
        return JsonResponse({"ok": False, "error": "expired"}, status=401)

    employee = Employee.objects.filter(employee_code=token.get("employee_code", "")).first()
    if employee is None:
        request.session.pop(KIOSK_ACTION_TOKEN_KEY, None)
        return JsonResponse({"ok": False, "error": "locked"}, status=401)

    idempotency_key = request.POST.get("idempotency_key", "")
    if not idempotency_key:
        return JsonResponse({"ok": False, "error": "missing_idempotency_key"}, status=400)

    try:
        event = record_punch(
            employee=employee,
            kind=request.POST.get("kind", ""),
            idempotency_key=idempotency_key,
            device=device,
        )
    except InvalidPunch as exc:
        return JsonResponse({"ok": False, "error": exc.code}, status=409)
    finally:
        # One unlock == one action: consume the token regardless of outcome.
        request.session.pop(KIOSK_ACTION_TOKEN_KEY, None)

    return JsonResponse({"ok": True, "kind": event.kind})
