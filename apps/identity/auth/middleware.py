"""Manager session lifetime enforcement.

Django's session cookie alone does not bound *inactivity* or a hard ceiling. This
middleware, for authenticated managers, logs the user out when either:

- **idle** longer than ``SESSION_IDLE_TIMEOUT`` (default 15 min), or
- the session is older than ``SESSION_ABSOLUTE_TIMEOUT`` (default 8 h),

whichever comes first. Timestamps are stamped at login by the MFA view.
"""

from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.contrib.auth import logout
from django.utils import timezone

LOGIN_AT_KEY = "_auth_login_at"
LAST_ACTIVITY_KEY = "_auth_last_activity"

IDLE_TIMEOUT = getattr(settings, "SESSION_IDLE_TIMEOUT", timedelta(minutes=15))
ABSOLUTE_TIMEOUT = getattr(settings, "SESSION_ABSOLUTE_TIMEOUT", timedelta(hours=8))


def _parse(value: str | None):
    if not value:
        return None
    from django.utils.dateparse import parse_datetime

    return parse_datetime(value)


class SessionTimeoutMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            now = timezone.now()
            login_at = _parse(request.session.get(LOGIN_AT_KEY))
            last_activity = _parse(request.session.get(LAST_ACTIVITY_KEY))

            expired = (
                login_at is None
                or last_activity is None
                or now - login_at > ABSOLUTE_TIMEOUT
                or now - last_activity > IDLE_TIMEOUT
            )
            if expired:
                logout(request)
            else:
                request.session[LAST_ACTIVITY_KEY] = now.isoformat()

        return self.get_response(request)


def stamp_login(session) -> None:
    """Record login + activity timestamps; call right after a manager logs in."""
    now = timezone.now().isoformat()
    session[LOGIN_AT_KEY] = now
    session[LAST_ACTIVITY_KEY] = now
