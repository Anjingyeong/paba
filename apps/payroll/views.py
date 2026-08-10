from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_GET, require_POST

from apps.exports.package import build_export_zip
from apps.identity.models import Employee
from apps.payroll.services.close import checksum_of
from apps.payroll.services.preview import (
    PayrollMonthError,
    monthly_payroll_lines,
    parse_month,
    set_hourly_wage,
    statement_from_line,
)


def _staff_only(request: HttpRequest) -> HttpResponse | None:
    if not isinstance(request.user, User) or not request.user.is_staff:
        return HttpResponseForbidden("접근 권한이 없습니다.")
    return None


@login_required
@require_POST
def update_hourly_wage(request: HttpRequest) -> HttpResponse:
    denied = _staff_only(request)
    if denied is not None:
        return denied
    try:
        month = parse_month(request.POST.get("month", ""))
        amount = int(request.POST.get("hourly_wage", ""))
    except (PayrollMonthError, ValueError):
        return HttpResponseBadRequest("월과 시급을 확인해주세요.")
    if amount <= 0:
        return HttpResponseBadRequest("시급은 0보다 커야 합니다.")
    employee = get_object_or_404(Employee, employee_code=request.POST.get("employee_code", ""))
    set_hourly_wage(employee, month, amount)
    return redirect(f"/manager/console/?month={month:%Y-%m}#preview")


@login_required
@require_GET
def download_statements(request: HttpRequest) -> HttpResponse:
    denied = _staff_only(request)
    if denied is not None:
        return denied
    try:
        month = parse_month(request.GET.get("month", ""))
    except PayrollMonthError:
        return HttpResponseBadRequest("월을 확인해주세요.")

    lines = monthly_payroll_lines(month)
    if not lines or any(not line.ready for line in lines):
        return HttpResponse("시급 또는 근태 기록을 먼저 확인해주세요.", status=409)
    payload = {
        "month": f"{month:%Y-%m}",
        "lines": [
            {
                "employee_id": line.employee_code,
                "hours": str(line.total_hours),
                "gross": line.gross_pay,
            }
            for line in lines
        ],
    }
    checksum = checksum_of(payload)
    statements = [statement_from_line(line, month, checksum) for line in lines]
    archive, _manifest = build_export_zip(
        month_label=f"{month:%Y-%m}",
        statements=statements,
        snapshot_version=1,
        checksum=checksum,
    )
    response = HttpResponse(archive, content_type="application/zip")
    response["Content-Disposition"] = f'attachment; filename="payroll-{month:%Y-%m}.zip"'
    return response
