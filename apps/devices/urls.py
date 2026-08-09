from __future__ import annotations

from django.urls import path

from . import views

app_name = "devices"

urlpatterns = [
    path("manager/devices/pair/", views.device_pair, name="pair"),
    path("kiosk/activate/", views.kiosk_activate, name="kiosk_activate"),
    path("kiosk/unlock/", views.kiosk_unlock, name="kiosk_unlock"),
]
