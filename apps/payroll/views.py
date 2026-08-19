from __future__ import annotations

from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_GET, require_POST

from apps.core.models import Store
from apps.exports.services import create_export
from apps.identity.models import Employee
from apps.payroll.models import PayrollPeriod, PeriodStatus
from apps.payroll.services.close import (
    CloseBlocked,
    close_period,
    latest_snapshot,
    prepare_period,
    reopen_period,
)
from apps.payroll.services.month_close import PayrollBuildBlocked, build_month_payload
from apps.payroll.services.preview import (
    PayrollMonthError,
    parse_month,
    set_hourly_wage,
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
@require_POST
def update_payroll_settings(request: HttpRequest) -> HttpResponse:
    denied = _staff_only(request)
    if denied is not None:
        return denied
    raw_pay_day = request.POST.get("payroll_pay_day", "").strip()
    try:
        pay_day = int(raw_pay_day)
    except ValueError:
        return HttpResponseBadRequest("급여 지급일을 확인해주세요.")
    if not 1 <= pay_day <= 28:
        return HttpResponseBadRequest("급여 지급일은 1~28일이어야 합니다.")

    store = Store.get()
    store.payroll_pay_day = pay_day
    store.auto_payroll_close_enabled = request.POST.get("auto_payroll_close_enabled") == "on"
    store.full_clean()
    store.save(update_fields=["payroll_pay_day", "auto_payroll_close_enabled", "updated_at"])
    messages.success(request, "월 급여 자동화 설정을 저장했습니다.")
    return redirect("/manager/console/#preview")


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

    period = PayrollPeriod.objects.filter(month=month).first()
    if period is None or period.status != PeriodStatus.CLOSED:
        return HttpResponse("월마감이 완료된 급여만 다운로드할 수 있습니다.", status=409)
    snapshot = latest_snapshot(period)
    if snapshot is None:
        return HttpResponse("마감 스냅샷이 없습니다.", status=409)
    _manifest, archive = create_export(snapshot=snapshot, requester=request.user)
    response = HttpResponse(archive, content_type="application/zip")
    response["Content-Disposition"] = f'attachment; filename="payroll-{month:%Y-%m}.zip"'
    return response


@login_required
@require_POST
def close_month(request: HttpRequest) -> HttpResponse:
    denied = _staff_only(request)
    if denied is not None:
        return denied
    try:
        month = parse_month(request.POST.get("month", ""))
        pay_date = date.fromisoformat(request.POST.get("pay_date", ""))
    except (PayrollMonthError, ValueError):
        return HttpResponseBadRequest("월과 지급일을 확인해주세요.")
    try:
        payload = build_month_payload(month, pay_date=pay_date)
        period = prepare_period(month)
        snapshot = close_period(
            period=period,
            payload=payload,
            reason=request.POST.get("reason", "").strip(),
        )
    except PayrollBuildBlocked as exc:
        messages.error(request, f"급여 계산 확인 필요: {', '.join(exc.blockers)}")
        return redirect(f"/manager/console/?month={month:%Y-%m}#preview")
    except CloseBlocked as exc:
        messages.error(request, f"월마감 불가: {', '.join(exc.blockers)}")
        return redirect(f"/manager/console/?month={month:%Y-%m}#preview")
    messages.success(request, f"{month:%Y-%m} 급여를 v{snapshot.version}으로 마감했습니다.")
    return redirect(f"/manager/console/?month={month:%Y-%m}#preview")


@login_required
@require_POST
def reopen_month(request: HttpRequest) -> HttpResponse:
    denied = _staff_only(request)
    if denied is not None:
        return denied
    try:
        month = parse_month(request.POST.get("month", ""))
    except PayrollMonthError:
        return HttpResponseBadRequest("월을 확인해주세요.")
    reason = request.POST.get("reason", "").strip()
    if not reason:
        return HttpResponseBadRequest("재오픈 사유를 입력해주세요.")
    period = get_object_or_404(PayrollPeriod, month=month)
    reopen_period(period=period, reason=reason)
    messages.success(request, f"{month:%Y-%m} 급여를 수정 가능 상태로 되돌렸습니다.")
    return redirect(f"/manager/console/?month={month:%Y-%m}#preview")
