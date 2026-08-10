from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from apps.attendance.services.manual_shifts import (
    ManualShiftConflict,
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
