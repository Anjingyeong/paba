from __future__ import annotations

from django.urls import path

from . import manual_views, views

app_name = "attendance"

urlpatterns = [
    path("kiosk/punch/", views.kiosk_punch, name="kiosk_punch"),
    path(
        "manager/attendance/manual/",
        manual_views.create_manual_shift,
        name="create_manual_shift",
    ),
]
