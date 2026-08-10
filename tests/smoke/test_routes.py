"""The server-rendered kiosk and manager console shells are reachable."""

from __future__ import annotations

from datetime import date

import pytest
from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.test import Client

from apps.attendance.models import Shift
from apps.devices.models import KioskDevice
from apps.identity.auth.middleware import stamp_login
from apps.identity.models import AccountRole, Employee


def test_home_renders_frontend_entry_points(client: Client) -> None:
    response = client.get("/")

    assert response.status_code == 200
    content = response.content.decode()
    assert 'class="pb-landing"' in content
    assert 'href="/kiosk/"' in content
    assert 'href="/manager/console/"' in content


@pytest.mark.django_db
def test_kiosk_home_renders(client: Client) -> None:
    response = client.get("/kiosk/")
    assert response.status_code == 200
    assert b"pb-kiosk" in response.content


@pytest.mark.django_db
def test_kiosk_live_context(client: Client) -> None:
    secret = "live-kiosk-secret"
    device = KioskDevice.objects.create(
        name="LIVE-KIOSK-01",
        secret_hash=make_password(secret),
    )
    KioskDevice.objects.create(name="OTHER-KIOSK-02", secret_hash=make_password("other-secret"))
    client.cookies[settings.KIOSK_COOKIE_NAME] = f"{device.pk}:{secret}"
    Employee.objects.create(
        employee_code="HIDDEN-EMP-01",
        display_name="Must not be listed",
        hire_date=date(2025, 1, 1),
    )

    response = client.get("/kiosk/")

    content = response.content.decode()
    assert "LIVE-KIOSK-01" in content
    assert "OTHER-KIOSK-02" not in content
    assert "HIDDEN-EMP-01" not in content
    assert content.count("data-device-state") == 1


@pytest.mark.django_db
def test_kiosk_empty_state(client: Client) -> None:
    response = client.get("/kiosk/")

    content = response.content.decode()
    assert "실시간 기기 상태가 없습니다." in content
    assert "data-device-state" not in content


def _authenticate_manager(client: Client, manager: User) -> None:
    client.force_login(manager)
    session = client.session
    stamp_login(session)
    session.save()


@pytest.mark.django_db
def test_manager_console_requires_login(client: Client) -> None:
    response = client.get("/manager/console/")
    assert response.status_code == 302
    assert "/manager/login/" in response.headers["Location"]


@pytest.mark.django_db
def test_manager_console_rejects_non_staff(client: Client) -> None:
    user = User.objects.create_user(username="nonstaff-manager")
    _authenticate_manager(client, user)

    response = client.get("/manager/console/")

    assert response.status_code == 403


@pytest.mark.django_db
def test_manager_console_live_context(client: Client) -> None:
    manager = User.objects.create_user(username="live-manager", is_staff=True)
    Employee.objects.create(
        employee_code="LIVE-MANAGER",
        display_name="Live manager",
        hire_date=date(2025, 1, 1),
        account_role=AccountRole.MANAGER,
        user=manager,
    )
    attendee = Employee.objects.create(
        employee_code="LIVE-ATTEND-01",
        display_name="Live attendee",
        hire_date=date(2025, 1, 1),
    )
    Shift.objects.create(employee=attendee)
    _authenticate_manager(client, manager)

    response = client.get("/manager/console/")

    assert response.status_code == 200
    content = response.content.decode()
    assert "LIVE-ATTEND-01" in content
    assert content.count("<tr data-attendance-row>") == 1


@pytest.mark.django_db
def test_manager_console_empty_state(client: Client) -> None:
    manager = User.objects.create_user(username="empty-manager", is_staff=True)
    _authenticate_manager(client, manager)

    response = client.get("/manager/console/")

    assert response.status_code == 200
    content = response.content.decode()
    assert "표시할 실시간 근태 기록이 없습니다." in content
    assert "<tr data-attendance-row>" not in content
