"""Root URL configuration. Health probes live at the top level for load balancers."""

from __future__ import annotations

from django.urls import include, path

urlpatterns = [
    path("health/", include("apps.health.urls")),
]
