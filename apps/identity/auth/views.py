"""Manager authentication flows: password → TOTP → session, plus re-auth.

Login is two-step: a correct password moves the user to the MFA step (their id is
held in the session, not logged in yet); only a valid TOTP completes login, at
which point Django rotates the session key and the lifetime timestamps are
stamped. Error messages are deliberately generic so they never reveal whether a
username exists or which factor failed.
"""

from __future__ import annotations

from typing import cast

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from . import services
from .middleware import stamp_login

PENDING_MFA_KEY = "_pending_mfa_user_id"
REAUTH_AT_KEY = "_reauth_at"
GENERIC_ERROR = "로그인 정보가 올바르지 않습니다."


@require_http_methods(["GET", "POST"])
def manager_login(request: HttpRequest) -> HttpResponse:
    if request.method == "GET":
        return render(request, "auth/login.html")

    user = authenticate(
        request,
        username=request.POST.get("username", ""),
        password=request.POST.get("password", ""),
    )
    # Only staff/managers with a confirmed TOTP may proceed; anything else is a
    # generic failure that reveals nothing.
    if user is None or not services.has_confirmed_totp(cast(User, user)):
        return render(request, "auth/login.html", {"error": GENERIC_ERROR}, status=401)

    request.session[PENDING_MFA_KEY] = user.pk
    return redirect("auth:mfa")


@require_http_methods(["GET", "POST"])
def manager_mfa(request: HttpRequest) -> HttpResponse:
    user_id = request.session.get(PENDING_MFA_KEY)
    if not user_id:
        return redirect("auth:login")

    user = User.objects.filter(pk=user_id).first()
    if user is None:
        request.session.pop(PENDING_MFA_KEY, None)
        return redirect("auth:login")

    if request.method == "GET":
        return render(request, "auth/mfa.html")

    # Throttle the TOTP step so a known password can't be paired with a brute-forced
    # code. Lockout is stored in the DB (shared across app instances).
    if services.mfa_is_locked(user):
        return render(request, "auth/mfa.html", {"error": GENERIC_ERROR}, status=429)

    token = request.POST.get("token", "")
    recovery = request.POST.get("recovery_code", "")
    ok = services.verify_totp(user, token) if token else services.verify_recovery_code(
        user, recovery
    )
    if not ok:
        services.mfa_record_failure(user)
        return render(request, "auth/mfa.html", {"error": GENERIC_ERROR}, status=401)

    services.mfa_record_success(user)
    request.session.pop(PENDING_MFA_KEY, None)
    login(request, user)  # rotates the session key
    stamp_login(request.session)
    return HttpResponse("ok")


@require_http_methods(["POST"])
def manager_logout(request: HttpRequest) -> HttpResponse:
    logout(request)
    return redirect("auth:login")


@login_required
@require_http_methods(["POST"])
def manager_reauth(request: HttpRequest) -> HttpResponse:
    """Step-up verification for sensitive actions (settings, exports)."""
    token = request.POST.get("token", "")
    if not services.verify_totp(cast(User, request.user), token):
        return HttpResponse(status=401)
    request.session[REAUTH_AT_KEY] = timezone.now().isoformat()
    return HttpResponse("ok")
