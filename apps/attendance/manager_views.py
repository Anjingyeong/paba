from __future__ import annotations

from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.attendance.models import PunchKind, Shift
from apps.attendance.services import approvals, corrections
from apps.attendance.services.time_calculation import calculate


def _staff_only(request: HttpRequest) -> HttpResponse | None:
    if not isinstance(request.user, User) or not request.user.is_staff:
        return HttpResponseForbidden("접근 권한이 없습니다.")
    return None


def _redirect() -> HttpResponse:
    return redirect("/manager/console/#work-hours")


def _event_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    return timezone.make_aware(parsed) if timezone.is_naive(parsed) else timezone.localtime(parsed)


def manager_attendance_rows() -> list[dict]:
    rows: list[dict] = []
    shifts = Shift.objects.select_related("employee").order_by("-opened_at", "-pk")
    for shift in shifts:
        events = corrections.effective_events(shift)
        time_result = calculate(events)
        start = next((e for e in events if e.get("kind") == PunchKind.CLOCK_IN), None)
        end = next((e for e in reversed(events) if e.get("kind") == PunchKind.CLOCK_OUT), None)
        started_at = _event_datetime(start["occurred_at"]) if start else shift.opened_at
        ended_at = _event_datetime(end["occurred_at"]) if end else None
        rows.append(
            {
                "shift_id": shift.pk,
                "employee": shift.employee,
                "started_at": started_at,
                "ended_at": ended_at,
                "started_input": timezone.localtime(started_at).strftime("%Y-%m-%dT%H:%M"),
                "ended_input": (
                    timezone.localtime(ended_at).strftime("%Y-%m-%dT%H:%M") if ended_at else ""
                ),
                "is_open": shift.is_open,
                "approval_status": approvals.approval_status(shift),
                "worked_hours": time_result.total_hours if time_result.ok else None,
            }
        )
    return rows


@login_required
@require_POST
def approve_shift(request: HttpRequest, shift_id: int) -> HttpResponse:
    denied = _staff_only(request)
    if denied is not None:
        return denied
    shift = get_object_or_404(Shift.objects.select_related("employee"), pk=shift_id)
    if shift.is_open:
        messages.error(
            request,
            "근무 중인 기록은 승인할 수 없습니다. 먼저 퇴근 기록을 확인해주세요.",
        )
        return _redirect()
    result = calculate(corrections.effective_events(shift))
    if not result.ok:
        messages.error(request, "근태 순서가 올바르지 않아 승인할 수 없습니다.")
        return _redirect()
    approvals.approve_shift(manager=request.user, shift=shift)
    messages.success(request, f"{shift.employee.display_name}의 근태를 승인했습니다.")
    return _redirect()


@login_required
@require_POST
def correct_shift_times(request: HttpRequest, shift_id: int) -> HttpResponse:
    denied = _staff_only(request)
    if denied is not None:
        return denied
    shift = get_object_or_404(Shift.objects.select_related("employee"), pk=shift_id)
    if shift.is_open:
        messages.error(request, "근무 중인 기록은 시간 수정할 수 없습니다.")
        return _redirect()

    try:
        started_at = _event_datetime(request.POST.get("started_at", ""))
        ended_at = _event_datetime(request.POST.get("ended_at", ""))
    except ValueError:
        messages.error(request, "출근·퇴근 시간을 확인해주세요.")
        return _redirect()
    reason = request.POST.get("reason", "").strip()
    if not reason:
        messages.error(request, "수정 사유를 입력해주세요.")
        return _redirect()
    if ended_at <= started_at:
        messages.error(request, "퇴근 시간은 출근 시간보다 늦어야 합니다.")
        return _redirect()

    corrected_events: list[dict] = []
    saw_in = False
    saw_out = False
    for event in corrections.effective_events(shift):
        item = dict(event)
        if item.get("kind") == PunchKind.CLOCK_IN and not saw_in:
            item["occurred_at"] = started_at.isoformat()
            saw_in = True
        if item.get("kind") == PunchKind.CLOCK_OUT:
            item["occurred_at"] = ended_at.isoformat()
            saw_out = True
        corrected_events.append(item)
    if not saw_in or not saw_out:
        messages.error(request, "출근 또는 퇴근 원본 기록이 없어 시간 수정할 수 없습니다.")
        return _redirect()

    result = calculate(corrected_events)
    if not result.ok:
        messages.error(request, "수정한 시간이 휴게 기록과 충돌합니다. 시간을 다시 확인해주세요.")
        return _redirect()

    with transaction.atomic():
        corrections.create_correction(
            manager=request.user,
            shift=shift,
            corrected_events=corrected_events,
            reason=reason,
            evidence_note="manager console time correction",
        )
        approvals.approve_shift(manager=request.user, shift=shift)
    messages.success(request, f"{shift.employee.display_name}의 시간을 수정하고 승인했습니다.")
    return _redirect()