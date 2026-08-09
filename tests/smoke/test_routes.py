"""The server-rendered kiosk and manager console shells are reachable."""

from __future__ import annotations

import pytest
from django.test import Client


def test_kiosk_home_renders(client: Client) -> None:
    response = client.get("/kiosk/")
    assert response.status_code == 200
    assert b"pb-kiosk" in response.content


@pytest.mark.django_db
def test_manager_console_requires_login(client: Client) -> None:
    response = client.get("/manager/console/")
    assert response.status_code == 302
    assert "/manager/login/" in response.headers["Location"]
