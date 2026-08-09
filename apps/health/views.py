"""Load-balancer health probes.

- ``/health/live``  — the process is up and can serve a request. Never touches the DB.
- ``/health/ready`` — the app is ready to serve traffic: the database answers a
  trivial query. Returns 503 when the DB is unreachable.

Responses are deliberately minimal: a fixed JSON body with a status field and
nothing else. No secrets, settings, stack traces or exception text is exposed.
"""

from __future__ import annotations

from django.db import connection
from django.http import JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def liveness(_request) -> JsonResponse:
    return JsonResponse({"status": "live"}, status=200)


@require_GET
def readiness(_request) -> JsonResponse:
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:  # noqa: BLE001 - any DB error means "not ready", details are never leaked
        return JsonResponse({"status": "not-ready"}, status=503)
    return JsonResponse({"status": "ready"}, status=200)
