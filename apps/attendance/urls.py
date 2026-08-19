from __future__ import annotations

from django.urls import path

from . import manager_views, manual_views, views

app_name = "attendance"

urlpatterns = [
    path("kiosk/punch/", views.kiosk_punch, name="kiosk_punch"),
    path(
        "manager/attendance/manual/",
        manual_views.create_manual_shift,
        name="create_manual_shift",
    ),
    path(
        "manager/attendance/manual-week/",
        manual_views.create_manual_week,
        name="create_manual_week",
    ),
    path(
        "manager/attendance/<int:shift_id>/approve/",
        manager_views.approve_shift,
        name="approve_shift",
    ),
    path(
        "manager/attendance/<int:shift_id>/correct-times/",
        manager_views.correct_shift_times,
        name="correct_shift_times",
    ),
]
