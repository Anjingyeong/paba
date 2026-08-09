"""Attach a per-request id used to correlate audit entries and log lines."""

from __future__ import annotations

import uuid

REQUEST_ID_HEADER = "HTTP_X_REQUEST_ID"


class RequestIdMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.request_id = request.META.get(REQUEST_ID_HEADER) or uuid.uuid4().hex
        response = self.get_response(request)
        response.headers["X-Request-ID"] = request.request_id
        return response
