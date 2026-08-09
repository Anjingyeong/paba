from __future__ import annotations

from django.urls import path

from . import views

app_name = "attendance"

urlpatterns = [
    path("kiosk/punch/", views.kiosk_punch, name="kiosk_punch"),
]
