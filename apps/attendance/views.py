"""Kiosk punch endpoint.

Accepts a single punch only from a paired device that also presents a valid,
unexpired one-shot action token (minted by ``/kiosk/unlock/`` in Todo 4). The
token is consumed on success, so the employee never holds a durable session and
each unlock authorizes exactly one action.
"""

from __future__ import annotations

from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.http import require_POST

from apps.devices.views import KIOSK_ACTION_TOKEN_KEY, device_from_request
from apps.identity.models import Employee

from .models import Shift
from .services.punches import InvalidPunch, record_punch


def attendance_rows() -> QuerySet[Shift]:
    return Shift.objects.select_related("employee").order_by("-opened_at", "-pk")


def manager_console(request: HttpRequest) -> HttpResponse:
    if not request.user.is_staff:
        return HttpResponseForbidden("접근 권한이 없습니다.")
    return render(request, "manager/console.html", {"attendance_rows": attendance_rows()})


@require_POST
def kiosk_punch(request: HttpRequest) -> JsonResponse:
    device = device_from_request(request)
    if device is None:
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
