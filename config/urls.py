"""Root URL configuration. Health probes live at the top level for load balancers."""

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.urls import include, path

from apps.attendance.views import manager_console
from apps.devices.views import kiosk_home

urlpatterns = [
    path("health/", include("apps.health.urls")),
    path("kiosk/", kiosk_home, name="kiosk_home"),
    path(
        "manager/console/",
        login_required(manager_console),
        name="manager_console",
    ),
    path("manager/", include("apps.identity.auth.urls")),
    path("", include("apps.devices.urls")),
    path("", include("apps.attendance.urls")),
]
