"""Kiosk pairing and unlock endpoints.

- A logged-in manager issues a one-time pairing code.
- An unpaired tablet posts that code to ``/kiosk/activate/``; on success the server
  sets the ``__Host-kiosk`` cookie carrying ``"<device_id>:<secret>"`` and stores
  only the secret's hash.
- ``/kiosk/unlock/`` accepts an employee code + PIN, but only from a request that
  presents a valid, non-revoked device cookie. Success mints a one-shot,
  short-lived action token in the session that the punch flow (Todo 6) consumes;
  the employee is never given a durable session.
"""

from __future__ import annotations

from datetime import timedelta
from typing import cast

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.identity.auth.services import verify_employee_pin

from . import services
from .models import KioskDevice

KIOSK_ACTION_TOKEN_KEY = "_kiosk_action"  # noqa: S105 - session key name, not a secret
KIOSK_ACTION_TTL = timedelta(minutes=2)
GENERIC_UNLOCK_ERROR = "직원코드 또는 PIN이 올바르지 않습니다."


def device_states(request: HttpRequest) -> QuerySet[KioskDevice]:
    device = device_from_request(request)
    if device is None:
        return KioskDevice.objects.none()
    return KioskDevice.objects.filter(pk=device.pk)


def kiosk_home(request: HttpRequest) -> HttpResponse:
    return render(request, "kiosk/states.html", {"device_states": device_states(request)})


def device_from_request(request: HttpRequest) -> KioskDevice | None:
    raw = request.COOKIES.get(settings.KIOSK_COOKIE_NAME)
    if not raw or ":" not in raw:
        return None
    device_id, _, secret = raw.partition(":")
    try:
        return services.verify_device(int(device_id), secret)
    except ValueError:
        return None


@login_required
@require_http_methods(["GET", "POST"])
def device_pair(request: HttpRequest) -> HttpResponse:
    if request.method == "GET":
        return render(request, "devices/pair.html")
    code = services.create_pairing_code(cast(User, request.user))
    return render(request, "devices/pair.html", {"code": code})


@require_http_methods(["POST"])
def kiosk_activate(request: HttpRequest) -> HttpResponse:
    result = services.activate_device(
        code=request.POST.get("code", ""),
        device_name=request.POST.get("device_name", "매장 태블릿"),
    )
    if result is None:
        return HttpResponse("페어링 코드가 올바르지 않습니다.", status=400)

    response = HttpResponse("paired")
    response.set_cookie(
        settings.KIOSK_COOKIE_NAME,
        f"{result.device.pk}:{result.device_secret}",
        secure=settings.KIOSK_COOKIE_SECURE,
        httponly=True,
        samesite=settings.KIOSK_COOKIE_SAMESITE,
        max_age=60 * 60 * 24 * 365,
    )
    return response


@require_http_methods(["POST"])
def kiosk_unlock(request: HttpRequest) -> JsonResponse:
    device = device_from_request(request)
    if device is None:
        return JsonResponse({"ok": False, "error": "unpaired"}, status=403)

    result = verify_employee_pin(
        employee_code=request.POST.get("employee_code", ""),
        pin=request.POST.get("pin", ""),
    )
    if not result.ok:
        return JsonResponse({"ok": False, "error": GENERIC_UNLOCK_ERROR}, status=401)

    # One-shot action token: consumed by the punch view, then discarded. No
    # durable employee session is ever created.
    request.session[KIOSK_ACTION_TOKEN_KEY] = {
        "employee_code": request.POST.get("employee_code", ""),
        "expires_at": (timezone.now() + KIOSK_ACTION_TTL).isoformat(),
    }
    return JsonResponse({"ok": True})
