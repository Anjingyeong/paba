"""Root URL configuration. Health probes live at the top level for load balancers."""

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.urls import include, path
from django.views.generic import TemplateView

urlpatterns = [
    path("health/", include("apps.health.urls")),
    # Server-rendered UI shells (assets load from STATIC_URL="/assets/").
    path("kiosk/", TemplateView.as_view(template_name="kiosk/states.html"), name="kiosk_home"),
    path(
        "manager/console/",
        login_required(TemplateView.as_view(template_name="manager/console.html")),
        name="manager_console",
    ),
    path("manager/", include("apps.identity.auth.urls")),
    path("", include("apps.devices.urls")),
    path("", include("apps.attendance.urls")),
]
