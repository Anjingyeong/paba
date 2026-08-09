"""Root URL configuration. Health probes live at the top level for load balancers."""

from __future__ import annotations

from django.urls import include, path

urlpatterns = [
    path("health/", include("apps.health.urls")),
    path("manager/", include("apps.identity.auth.urls")),
    path("", include("apps.devices.urls")),
    path("", include("apps.attendance.urls")),
]
