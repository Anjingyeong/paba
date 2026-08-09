"""Smoke tests for the application shell.

Written before the implementation (TDD): they assert the project boots, the
settings are wired, and the health probes behave — including the DB-failure
path where readiness must report 503 without leaking internals.
"""

from __future__ import annotations

import pytest
from django.test import Client


def test_settings_use_real_postgresql() -> None:
    """The domain relies on PostgreSQL-only features; SQLite is never allowed."""
    from django.conf import settings

    engine = settings.DATABASES["default"]["ENGINE"]
    assert engine == "django.db.backends.postgresql"


def test_liveness_is_up_without_touching_db(client: Client) -> None:
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "live"}


@pytest.mark.django_db
def test_readiness_ok_when_db_reachable(client: Client) -> None:
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


@pytest.mark.django_db
def test_readiness_503_and_leaks_nothing_when_db_down(client: Client, monkeypatch) -> None:
    """When the DB is unreachable readiness returns 503 and exposes no internals."""
    from django.db import connection

    class _Boom:
        def __enter__(self):
            raise RuntimeError("secret-connection-string password=hunter2")

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(connection, "cursor", lambda: _Boom())

    response = client.get("/health/ready")
    assert response.status_code == 503
    body = response.content.decode()
    assert response.json() == {"status": "not-ready"}
    # No secret, password, or stack trace text leaks into the response body.
    assert "password" not in body
    assert "secret" not in body
    assert "Traceback" not in body
