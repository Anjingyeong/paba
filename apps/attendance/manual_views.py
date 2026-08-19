from __future__ import annotations

from datetime import date, datetime, time, timedelta
from uuid import NAMESPACE_URL, UUID, uuid5

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.attendance.services.approvals import approve_shift
from apps.attendance.services.manual_shifts import (
    ManualShiftConflict,
    ManualShiftInput,
    ManualShiftInputError,
    parse_manual_shift_input,
    record_manual_shift,
)
from apps.identity.models import Employee


@login_required
@require_POST
def create_manual_shift(request: HttpRequest) -> HttpResponse:
    """Create one manager-entered start/end work interval."""
    if not isinstance(request.user, User) or not request.user.is_staff:
        return HttpResponseForbidden("접근 권한이 없습니다.")
    try:
        entry = parse_manual_shift_input(request.POST)
    except ManualShiftInputError:
        return HttpResponseBadRequest("직원과 근무 시작·종료 시간을 확인해주세요.")

    employee = get_object_or_404(Employee, employee_code=entry.employee_code)
    try:
        record_manual_shift(employee=employee, entry=entry, actor_id=str(request.user.pk))
    except ManualShiftConflict:
        return HttpResponse("기존 근무 기록과 시간이 겹칩니다.", status=409)
    return redirect(f"/manager/console/?month={entry.started_at:%Y-%m}#attendance")


def _local_datetime(work_date: date, raw_time: str) -> datetime:
    parsed_time = time.fromisoformat(raw_time)
    return timezone.make_aware(datetime.combine(work_date, parsed_time))


@login_required
@require_POST
def create_manual_week(request: HttpRequest) -> HttpResponse:
    """Record up to seven manager-entered work intervals and approve them immediately."""
    if not isinstance(request.user, User) or not request.user.is_staff:
        return HttpResponseForbidden("접근 권한이 없습니다.")

    employee_code = request.POST.get("employee_code", "").strip()
    try:
        week_start = date.fromisoformat(request.POST.get("week_start", ""))
        batch_id = UUID(request.POST.get("batch_id", ""))
    except ValueError:
        return HttpResponseBadRequest("직원과 주차를 확인해주세요.")
    if not employee_code:
        return HttpResponseBadRequest("직원을 선택해주세요.")

    employee = get_object_or_404(Employee, employee_code=employee_code)
    entries: list[ManualShiftInput] = []
    for index in range(7):
        started_raw = request.POST.get(f"start_{index}", "").strip()
        ended_raw = request.POST.get(f"end_{index}", "").strip()
        if not started_raw and not ended_raw:
            continue
        if not started_raw or not ended_raw:
            return HttpResponseBadRequest("근무 시작과 종료 시간을 함께 입력해주세요.")
        try:
            work_date = week_start + timedelta(days=index)
            started_at = _local_datetime(work_date, started_raw)
            ended_at = _local_datetime(work_date, ended_raw)
        except ValueError:
            return HttpResponseBadRequest("근무 시간을 확인해주세요.")
        if ended_at == started_at:
            return HttpResponseBadRequest("시작과 종료 시간은 같을 수 없습니다.")
        if ended_at < started_at:
            ended_at += timedelta(days=1)
        entries.append(
            ManualShiftInput(
                employee_code=employee_code,
                started_at=started_at,
                ended_at=ended_at,
                note=request.POST.get(f"note_{index}", "").strip(),
                idempotency_key=uuid5(NAMESPACE_URL, f"{batch_id}:{work_date.isoformat()}"),
            )
        )

    if not entries:
        return HttpResponseBadRequest("입력된 근무시간이 없습니다.")

    try:
        with transaction.atomic():
            for entry in entries:
                shift = record_manual_shift(
                    employee=employee,
                    entry=entry,
                    actor_id=str(request.user.pk),
                )
                approve_shift(manager=request.user, shift=shift)
    except ManualShiftConflict:
        return HttpResponse("기존 근무 기록과 시간이 겹칩니다.", status=409)

    return redirect(
        f"/manager/console/?month={week_start:%Y-%m}&employee={employee_code}#attendance"
    )
